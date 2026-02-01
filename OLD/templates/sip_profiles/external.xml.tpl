<profile name="external">
  <gateways>
    <gateway name="provider-user1">
      <param name="username" value="${PROVIDER_USER1}"/>
      <param name="password" value="${PROVIDER_PASS1}"/>
      <param name="realm" value="${PROVIDER_HOST}"/>
      <param name="proxy" value="${PROVIDER_HOST}"/>
      <param name="register" value="true"/>
    </gateway>
    <gateway name="provider-user2">
      <param name="username" value="${PROVIDER_USER2}"/>
      <param name="realm" value="${PROVIDER_HOST}"/>
      <param name="proxy" value="${PROVIDER_HOST}"/>
      <param name="register" value="false"/>
    </gateway>
  </gateways>
  <settings>
    <param name="sip-ip" value="${EXTERNAL_IP}"/>
    <param name="rtp-ip" value="${EXTERNAL_IP}"/>
    <param name="sip-port" value="${SIP_PORT}"/>
    <param name="auth-calls" value="false"/>
    <param name="context" value="public"/>
  </settings>
</profile>
