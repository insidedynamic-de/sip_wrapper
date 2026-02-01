<include>
  <extension name="user1_to_provider">
    <condition field="caller_id_number" expression="^aiptrunk-user1$">
      <condition field="destination_number" expression="^(.*)$">
        <action application="bridge" data="sofia/gateway/provider/$1"/>
      </condition>
    </condition>
  </extension>
  <extension name="user2_to_provider">
    <condition field="caller_id_number" expression="^aiptrunk-user2$">
      <condition field="destination_number" expression="^(.*)$">
        <action application="bridge" data="sofia/gateway/provider/$1"/>
      </condition>
    </condition>
  </extension>
</include>
