-- Strict user authentication script for FreeSWITCH
-- This script validates that the registering username exists in the directory
-- Place in: /etc/freeswitch/scripts/auth_user.lua

local json = require("cjson")

-- Config file path
local CONFIG_FILE = "/var/lib/freeswitch/wrapper_config.json"

-- Log function
local function log(level, msg)
    freeswitch.consoleLog(level, "[AUTH] " .. msg .. "\n")
end

-- Load users from config
local function load_users()
    local file = io.open(CONFIG_FILE, "r")
    if not file then
        log("ERR", "Cannot open config file: " .. CONFIG_FILE)
        return {}
    end

    local content = file:read("*all")
    file:close()

    local ok, config = pcall(json.decode, content)
    if not ok or not config then
        log("ERR", "Failed to parse config JSON")
        return {}
    end

    local users = {}
    if config.users then
        for _, user in ipairs(config.users) do
            if user.username and user.password and user.enabled ~= false then
                users[user.username] = {
                    password = user.password,
                    extension = user.extension or user.username
                }
            end
        end
    end

    log("INFO", "Loaded " .. table.getn(users) .. " users from config")
    return users
end

-- Main auth function
local function auth_user(username, domain, password_param)
    log("INFO", "Auth request for user: " .. tostring(username) .. "@" .. tostring(domain))

    -- Load users
    local users = load_users()

    -- Check if user exists
    local user = users[username]
    if not user then
        log("WARNING", "REJECTED: User '" .. tostring(username) .. "' does not exist in directory")
        return nil  -- Return nil to reject
    end

    log("INFO", "User '" .. username .. "' found, allowing authentication")

    -- Return user info for FreeSWITCH to verify password
    return {
        password = user.password,
        extension = user.extension
    }
end

-- FreeSWITCH calls this
local username = session:getVariable("sip_auth_username") or session:getVariable("sip_from_user")
local domain = session:getVariable("sip_auth_realm") or session:getVariable("domain_name")

local result = auth_user(username, domain, nil)

if result then
    -- Set variables for FreeSWITCH
    session:setVariable("user_exists", "true")
    session:setVariable("password", result.password)
else
    -- Reject registration
    session:setVariable("user_exists", "false")
    session:hangup("CALL_REJECTED")
end
