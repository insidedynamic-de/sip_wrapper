<gateway name="provider">
  <param name="proxy" value="${PROVIDER_HOST}:${PROVIDER_PORT}"/>
  <param name="register" value="${PROVIDER_USERNAME:+true}${PROVIDER_USERNAME:-false}"/>
  <param name="username" value="${PROVIDER_USERNAME}"/>
  <param name="password" value="${PROVIDER_PASSWORD}"/>
  <param name="realm" value="${PROVIDER_HOST}"/>
  <param name="from-domain" value="${PROVIDER_HOST}"/>
  <param name="expire-seconds" value="3600"/>
  <param name="extension" value="${SIP_USER}"/>
  <param name="caller-id-in-from" value="true"/>
  <param name="contact-params" value="transport=${PROVIDER_TRANSPORT}"/>
</gateway>
