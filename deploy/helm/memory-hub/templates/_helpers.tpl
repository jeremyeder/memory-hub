{{/*
Common labels
*/}}
{{- define "memory-hub.labels" -}}
app.kubernetes.io/part-of: memoryhub
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{/*
Build a fully-qualified image reference for a MemoryHub-built component.
Usage: {{ include "memory-hub.image" (dict "root" $ "img" .Values.mcp.image) }}
*/}}
{{- define "memory-hub.image" -}}
{{- $registry := .root.Values.global.imageRegistry -}}
{{- printf "%s/%s:%s" $registry .img.repository (.img.tag | toString) -}}
{{- end -}}

{{/*
Image pull policy for a component (falls back to the global default).
Usage: {{ include "memory-hub.pullPolicy" (dict "root" $ "img" .Values.mcp.image) }}
*/}}
{{- define "memory-hub.pullPolicy" -}}
{{- default .root.Values.global.imagePullPolicy .img.pullPolicy -}}
{{- end -}}

{{/*
Derive a Route host.
Usage: {{ include "memory-hub.routeHost" (dict "root" $ "name" "memory-hub-mcp" "ns" .Values.namespaces.mcp "explicit" .Values.mcp.route.host) }}
Returns "" when neither an explicit host nor global.routeDomain is set (OpenShift auto-assigns).
*/}}
{{- define "memory-hub.routeHost" -}}
{{- if .explicit -}}
{{- .explicit -}}
{{- else if .root.Values.global.routeDomain -}}
{{- printf "%s-%s.%s" .name .ns .root.Values.global.routeDomain -}}
{{- end -}}
{{- end -}}

{{/*
Effective auth-server public base URL (https://<host>), or "" if not derivable.
*/}}
{{- define "memory-hub.authServerUrl" -}}
{{- $host := include "memory-hub.routeHost" (dict "root" .root "name" "auth-server" "ns" .root.Values.namespaces.auth "explicit" .root.Values.auth.route.host) -}}
{{- if $host -}}https://{{ $host }}{{- end -}}
{{- end -}}

{{/*
MCP JWTVerifier issuer: explicit auth.oidc.issuerUrl, else the bundled auth server URL.
*/}}
{{- define "memory-hub.mcpIssuer" -}}
{{- if .Values.auth.oidc.issuerUrl -}}
{{- .Values.auth.oidc.issuerUrl -}}
{{- else -}}
{{- include "memory-hub.authServerUrl" (dict "root" .) -}}
{{- end -}}
{{- end -}}

{{/*
MCP JWTVerifier JWKS URI: explicit auth.oidc.jwksUrl, else <auth server>/.well-known/jwks.json.
*/}}
{{- define "memory-hub.mcpJwks" -}}
{{- if .Values.auth.oidc.jwksUrl -}}
{{- .Values.auth.oidc.jwksUrl -}}
{{- else -}}
{{- $base := include "memory-hub.authServerUrl" (dict "root" .) -}}
{{- if $base -}}{{ printf "%s/.well-known/jwks.json" $base }}{{- end -}}
{{- end -}}
{{- end -}}
