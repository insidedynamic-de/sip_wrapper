<include>
  <extension name="relay-inbound">
    <condition field="destination_number" expression="^.*$">
      <action application="bridge" data="sofia/gateway/provider/${destination_number}"/>
    </condition>
  </extension>
  <extension name="relay-outbound">
    <condition field="caller_id_number" expression="^${SIP_USER}$">
      <action application="bridge" data="sofia/gateway/provider/${destination_number}"/>
    </condition>
  </extension>
</include>
