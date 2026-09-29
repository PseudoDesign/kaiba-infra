{{- if ne .Token.iss @ISSUER@ }}{{ fail "unexpected issuer" }}{{ end -}}
{{- if not (regexMatch "^[a-zA-Z0-9_-]{1,128}$" .Token.sub) }}{{ fail "invalid stable subject" }}{{ end -}}
{{- $principal := printf "kaiba:person:%s" .Token.sub -}}
{{- if and .Insecure.CR.Type (ne .Insecure.CR.Type "user") }}{{ fail "only user certificates are authorized" }}{{ end -}}
{{- range .Insecure.CR.Principals -}}
{{- if ne . $principal }}{{ fail "requested principal is not authorized" }}{{ end -}}
{{- end -}}
{
  "type": "user",
  "keyId": {{ toJson (printf "%s#%s" .Token.iss .Token.sub) }},
  "principals": [{{ toJson $principal }}],
  "criticalOptions": {},
  "extensions": {"permit-pty": ""}
}
