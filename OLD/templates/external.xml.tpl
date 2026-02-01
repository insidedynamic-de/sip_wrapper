<profile name="external">
  <settings>
    <param name="sip-port" value="5080"/>
    <param name="rtp-ip" value="auto"/>
    <param name="sip-ip" value="auto"/>
    <param name="ext-rtp-ip" value="${EXTERNAL_IP:-auto}"/>
    <param name="ext-sip-ip" value="${EXTERNAL_IP:-auto}"/>
    <param name="auth-calls" value="false"/>
    <param name="dialplan" value="XML"/>
    <param name="context" value="default"/>
  </settings>
</profile>
