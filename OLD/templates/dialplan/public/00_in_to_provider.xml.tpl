<include>
  <extension name="in_to_user1">
    <condition field="destination_number" expression="^aiptrunk-user1$">
      <action application="bridge" data="sofia/gateway/provider/aiptrunk-user1"/>
    </condition>
  </extension>
  <extension name="in_to_user2">
    <condition field="destination_number" expression="^aiptrunk-user2$">
      <action application="bridge" data="sofia/gateway/provider/aiptrunk-user2"/>
    </condition>
  </extension>
</include>
