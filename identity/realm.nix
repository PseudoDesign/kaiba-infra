# Public configuration only. Users, passkeys and administrator credentials are
# runtime state; never put them in this import.
{ domain, realm, sshClientId, sshRedirectUris, enableDeviceAuthorization }:
let
  flow = "kaiba-passkey-only-v1";
in {
  inherit realm;
  displayName = "Kaiba";
  enabled = true;
  sslRequired = "all";
  registrationAllowed = false;
  resetPasswordAllowed = false;
  rememberMe = false;
  loginWithEmailAllowed = false;
  duplicateEmailsAllowed = false;
  editUsernameAllowed = false;
  bruteForceProtected = true;
  permanentLockout = false;
  failureFactor = 5;
  accessTokenLifespan = 300;
  ssoSessionIdleTimeout = 1800;
  ssoSessionMaxLifespan = 28800;
  revokeRefreshToken = true;
  refreshTokenMaxReuse = 0;
  actionTokenGeneratedByAdminLifespan = 600;
  eventsEnabled = true;
  eventsExpiration = 604800;
  adminEventsEnabled = true;
  adminEventsDetailsEnabled = false;
  webAuthnPolicyPasswordlessRpEntityName = "Kaiba";
  webAuthnPolicyPasswordlessRpId = domain;
  webAuthnPolicyPasswordlessSignatureAlgorithms = [ "ES256" "RS256" ];
  webAuthnPolicyPasswordlessAttestationConveyancePreference = "none";
  webAuthnPolicyPasswordlessAuthenticatorAttachment = "not specified";
  webAuthnPolicyPasswordlessRequireResidentKey = "Yes";
  webAuthnPolicyPasswordlessUserVerificationRequirement = "required";
  webAuthnPolicyPasswordlessAvoidSameAuthenticatorRegister = true;
  webAuthnPolicyPasswordlessCreateTimeout = 120;
  browserFlow = flow;
  roles.realm = [{ name = "kaiba-owner-enrolling"; }];
  authenticatorConfig = [{
    alias = "kaiba-enrollment-deny-others";
    config = { condUserRole = "kaiba-owner-enrolling"; negate = "true"; };
  }];
  authenticationFlows = [{
    alias = flow;
    description = "A user-verified discoverable passkey; no password or cookie alternative";
    providerId = "basic-flow";
    topLevel = true;
    builtIn = false;
    authenticationExecutions = [{
      authenticator = "webauthn-authenticator-passwordless";
      authenticatorFlow = false;
      requirement = "REQUIRED";
      priority = 10;
      userSetupAllowed = false;
    }];
   } {
    alias = "kaiba-owner-enrollment-v1";
    providerId = "basic-flow";
    topLevel = true;
    builtIn = false;
    authenticationExecutions = [{
      authenticator = "auth-username-password-form";
      authenticatorFlow = false;
      requirement = "REQUIRED";
      priority = 10;
      userSetupAllowed = false;
    } {
      flowAlias = "kaiba-owner-enrollment-deny-v1";
      authenticatorFlow = true;
      requirement = "CONDITIONAL";
      priority = 20;
    }];
  } {
    alias = "kaiba-owner-enrollment-deny-v1";
    providerId = "basic-flow";
    topLevel = false;
    builtIn = false;
    authenticationExecutions = [{
      authenticator = "conditional-user-role";
      authenticatorConfig = "kaiba-enrollment-deny-others";
      authenticatorFlow = false;
      requirement = "REQUIRED";
      priority = 10;
    } {
      authenticator = "deny-access-authenticator";
      authenticatorFlow = false;
      requirement = "REQUIRED";
      priority = 20;
    }];
  }];
  requiredActions = [{
    alias = "webauthn-register-passwordless";
    name = "Register a Kaiba passkey";
    providerId = "webauthn-register-passwordless";
    enabled = true;
    defaultAction = false;
    priority = 10;
    config = { };
  }];
  defaultDefaultClientScopes = [ "basic" "profile" "email" ];
  defaultOptionalClientScopes = [ ];
  groups = [ { name = "kaiba-ssh-admin"; } ];
  clients = [{
    clientId = sshClientId;
    name = "Kaiba SSH";
    enabled = true;
    protocol = "openid-connect";
    publicClient = true;
    standardFlowEnabled = true;
    directAccessGrantsEnabled = false;
    implicitFlowEnabled = false;
    serviceAccountsEnabled = false;
    fullScopeAllowed = false;
    redirectUris = sshRedirectUris;
    webOrigins = [ ];
    defaultClientScopes = [ "basic" "profile" "email" ];
    optionalClientScopes = [ ];
    attributes = {
      "pkce.code.challenge.method" = "S256";
      # Every SSH login must perform the passkey flow again; a refresh token
      # must not extend the ability to mint another eight-hour certificate.
      "use.refresh.tokens" = "false";
      "oauth2.device.authorization.grant.enabled" = if enableDeviceAuthorization then "true" else "false";
      "backchannel.logout.session.required" = "true";
      "post.logout.redirect.uris" = "";
    };
    protocolMappers = [{
      name = "kaiba-groups";
      protocol = "openid-connect";
      protocolMapper = "oidc-group-membership-mapper";
      consentRequired = false;
      config = {
        "claim.name" = "groups";
        "full.path" = "false";
        "id.token.claim" = "true";
        "access.token.claim" = "true";
        "userinfo.token.claim" = "true";
      };
    }];
  } {
    clientId = "kaiba-owner-enrollment";
    name = "Temporary owner passkey enrollment";
    enabled = false;
    protocol = "openid-connect";
    publicClient = true;
    standardFlowEnabled = true;
    directAccessGrantsEnabled = false;
    implicitFlowEnabled = false;
    serviceAccountsEnabled = false;
    fullScopeAllowed = false;
    redirectUris = [ "https://${domain}/realms/${realm}/account/" ];
    webOrigins = [ ];
    defaultClientScopes = [ "basic" "profile" ];
    optionalClientScopes = [ ];
    attributes = { "pkce.code.challenge.method" = "S256"; };
  }];
}
