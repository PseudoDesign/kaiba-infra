from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "identity"))
import forgejo_sso as sso


class ForgejoIdentityTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"Provider": "openidConnect", "ClientID": "kaiba-forgejo", "ClientSecret": "fixture-secret",
            "OpenIDConnectAutoDiscoveryURL": "https://auth.test/realms/kaiba/.well-known/openid-configuration",
            "RequiredClaimName": "sub", "RequiredClaimValue": "owner-subject", "SkipLocalTwoFA": True,
            "Scopes": ["openid", "profile", "email"]}

    def validate(self, policy):
        sso.validate_auth_source(policy, "kaiba-forgejo", "fixture-secret", "https://auth.test/realms/kaiba", "owner-subject")

    def test_provider_cannot_change_subject_secret_or_discovery(self):
        self.validate(self.policy)
        for field, value in [("RequiredClaimValue", "other-subject"), ("ClientSecret", "other-secret"),
                ("OpenIDConnectAutoDiscoveryURL", "https://attacker.example"), ("RequiredClaimName", "email")]:
            with self.subTest(field=field), self.assertRaises(sso.Refuse) as error:
                self.validate({**self.policy, field: value})
            self.assertNotIn("fixture-secret", str(error.exception))

    def test_additional_identity_mappings_are_rejected(self):
        for field in ["AdminGroup", "GroupTeamMap", "AttributeSSHPublicKey", "AllowUsernameChange"]:
            with self.subTest(field=field), self.assertRaises(sso.Refuse):
                self.validate({**self.policy, field: "unexpected"})

    def test_matching_name_cannot_claim_local_or_other_oidc_account(self):
        valid = [{"login": "owner", "source_id": 7, "login_name": "owner-subject"}]
        sso.validate_owner_binding(valid, "owner", 7, "owner-subject")
        for users in [[], valid + valid, [{**valid[0], "source_id": 0}], [{**valid[0], "login_name": "other-subject"}]]:
            with self.subTest(users=users), self.assertRaises(sso.Refuse):
                sso.validate_owner_binding(users, "owner", 7, "owner-subject")


if __name__ == "__main__":
    unittest.main()
