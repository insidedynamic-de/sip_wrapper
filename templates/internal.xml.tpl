<profile name="internal">
  <gateways>
    <gateway name="user">
      <param name="username" value="${SIP_USER}"/>
      <param name="password" value="${SIP_PASSWORD}"/>
      <param name="realm" value="${SIP_DOMAIN}"/>
      <param name="from-domain" value="${SIP_DOMAIN}"/>
      <param name="proxy" value="${SIP_DOMAIN}"/>
      <param name="register" value="true"/>
      <param name="expire-seconds" value="3600"/>
    </gateway>
  </gateways>
  <settings>
    <param name="sip-port" value="5060"/>
    <param name="rtp-ip" value="auto"/>
    <param name="sip-ip" value="auto"/>
    <param name="ext-rtp-ip" value="${EXTERNAL_IP:-auto}"/>
    <param name="ext-sip-ip" value="${EXTERNAL_IP:-auto}"/>
    <param name="auth-calls" value="true"/>
    <param name="dialplan" value="XML"/>
    <param name="context" value="default"/>
  </settings>
</profile>
