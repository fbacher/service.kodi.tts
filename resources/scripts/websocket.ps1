# $run_tests = $False
# $Global:file_num = 0

$Global:shutdown = $False  # If true, threads do orderly shutdown
Function Get_Queue_Request
{
    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $true)]
        [string]    $json_body_text,
        [Parameter(Position = 1, Mandatory = $False)]
        [switch]    $expect_result = $True
    )

    BEGIN
    {
        # Write-Log "Entering Get_Queue_Request"
        $shutting_down = $False
    }
    PROCESS
    {
        if ($Global:shutdown)
        {
            if (-not $shutting_down)
            {
                Write-Debug "Shutting down, JSON Rejected"
                $shutting_down = $True
            }
            return $null
        }
        try
        {
            $ws = New-Object Net.WebSockets.ClientWebSocket
            $cts = New-Object Threading.CancellationTokenSource
            $ct = New-Object Threading.CancellationToken($False)

            # Write-Debug "Connecting..."
            $connectTask = $ws.ConnectAsync("ws://127.0.0.1:9090/jsonrpc", $cts.Token)
            do
            {
                Start-Sleep -milliseconds 100
            }
            until ($connectTask.IsCompleted)
            # Write-Debug "Connected!"

            # Write-Debug "Sending message $json_body_text"
            # "Sending message: $json_body_text" | Out-File -FilePath "$env:homepath/logs.txt" -Append

            [ArraySegment[byte]]$msg = [System.Text.Encoding]::UTF8.GetBytes($json_body_text)
            # Write-Log "Calling SendAsync"
            $Async_Sender = $ws.SendAsync(
                    $msg,
                    [System.Net.WebSockets.WebSocketMessageType]::Binary,
                    $true,
                    $ct
            )
            if (-not $expect_result)
            {
                Write-Log "Returning without result"
                $json_result = $Null
            }
            else
            {
                $Async_Sender.GetAwaiter().GetResult() | Out-Null

                # Write-Log "Pre-ws.State: $( $ws.State ) $( $ws.State -eq [Net.WebSockets.WebSocketState]::Open ) End: $( $taskResult.Result.EndOfMessage )"

                $buffer = [Net.WebSockets.WebSocket]::CreateClientBuffer(1024, 1024)
                $taskResult = $null

                # while ($ws.State -eq [Net.WebSockets.WebSocketState]::Open)
                # {
                $json_string_result = [string]""
                try
                {
                    do
                    {
                        $taskResult = $ws.ReceiveAsync($buffer, $ct)
                        # Write-Log "Received chunk"
                        while (-not $taskResult.IsCompleted -and $ws.State -eq [Net.WebSockets.WebSocketState]::Open)
                        {
                            # Write-Log "taskResult: $taskResult"
                            [Threading.Thread]::Sleep(10)  # ms
                        }
                        $length = [int]$taskResult.Result.Count
                        # Write-Log "Length: $length"
                        [string]$str_buf = [string] [System.Text.Encoding]::UTF8.GetString($buffer, 0, $length)
                        $json_string_result += $str_buf
                    } until (
                    $ws.State -ne [Net.WebSockets.WebSocketState]::Open -or $taskResult.Result.EndOfMessage
                    )
                }
                catch
                {
                    Write-Log "Error reading json results."
                    Write-Log "$_.Exception.Message"
                }
                # Write-Log "ws.State: $( $ws.State ) $( $ws.State -eq [Net.WebSockets.WebSocketState]::Open ) End: $( $taskResult.Result.EndOfMessage )"

                if ( [string]::IsNullOrEmpty($json_string_result))
                {
                    Write-Debug "`n`n`n  N O   R E S U L T S  No Results returned xxxxxxxxxxxxxxxxxxx"
                    $result = $null
                }

                $json_result = ConvertFrom-Json -InputObject $json_string_result
                # Write-Log "jsonResult: $( json_result | Format-List |out-string )"
                if ($null -ne $( $json_result.error ))
                {
                    $error = $( $json_result.error )
                    # Write-Log "Got error"
                    $json_result = $null
                }
                else
                {
                    $result = $( $json_result.result )

                    if ($False)
                    {
                        Write-Debug "id: $jsonResult['id']"
                        Write-Debug "result: $( $jsonResult.result )"
                        Write-Host ($result | Format-List |out-string)
                        Write-Log "addons: $( $result.addons )"
                        Write-Host ($( $result.addons ) | Format-List |out-string)
                        $addons_list = $( $result.addons )
                        $addons_dict = $addons_list[0]
                        Write-Log "addons_dict: $addons_dict"

                        $addons = @{ }
                        foreach ($addons_dict in $addons_list)
                        {
                            Write-Debug "addons_dict: $addons_dict"
                            $key = $( $addons_dict.addonid )
                            $addons[$key] = $addons_dict
                        }
                        foreach ($key in $addons.keys)
                        {
                            Write-Debug "key: $key "
                            Write-Debug "value: $( $addons[$key] )"
                        }
                    }
                }
            }
        }
        finally
        {
            # Write-Log "Disposing Web Service"
            $ws.Dispose()
        }
    }
    END
    {
        # Write-Log "Exiting websocket Get_Queue_Request"
        return $json_result
    }
}

Function Get_Addon_Info
{
    BEGIN
    {
        # Write-Log "In websocket Get_Addon_Info"
        $json_text = @{
            "jsonrpc" = "2.0"
            "id" = 1
            "method" = "Addons.GetAddons"
            "params" = @{
                "properties" = @("name"
                    "version"
                    "enabled")
            }
        }

        $json_str = convertTo-Json -InputObject $json_text -compress
        $json_response = Get_Queue_Request $json_str
    }
    PROCESS
    {
        # Basic result of addons.getaddons:
        #    '{"id":1,"jsonrpc":"2.0","result":{"addons":[{"addonid":"audioencoder.kodi.builtin.aac"...}
        #
        # Create Hashtable of addon information. The key is the addon id and the value is a Hashtable
        # of: addonid,

        $result = $( $json_response.result )
        $addons_list = $( $result.addons )
        $addons_dict = @{ }
        foreach ($addon_dict in $addons_list)
        {
            # Write-Debug "addon_dict: $addon_dict"
            $key = $( $addon_dict.addonid )
            $addons_dict[$key] = $addon_dict
        }
        if ($False)
        {
            foreach ($key in $addons_dict.keys)
            {
                Write-Log "key: $key "
                Write-Log "value: $( $addons_dict[$key] )"
                Write-Log "addon-id: $( $( $addons_dict[$key] ).addonid )"
            }
        }
        return $addons_dict
    }

    END
    {
        # Write-Log "Exiting websocket Get_Addon_Info"
    }
}


Function Get_Addon_Details
{
    # Kodi's Addons.GetAddonDetails returns an error if given addon is not found. There error code
    # does not say why it failed. It therefore best to first see if the if the addon is known to Kodi
    # by using GetAddons first.

    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $true)]
        [string]    $addon_id
    )
    BEGIN
    {
        Write-Log "Entering Get_Addon_Details"

        # '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": '
        #            '{"addonid":"service.kodi.tts","properties": ["name","version","enabled"]}}')
        # if 'addon' not in data['result']:
        #            return False
        #        if 'enabled' not in data['result']['addon']:
        #            return False
        #        return data['result']['addon']['enabled']

        # Write-Log "In websocket Get_Addon_Details"
        $json_text = @{
            "jsonrpc" = "2.0"
            "id" = 1
            "method" = "Addons.GetAddonDetails"
            "params" = @{
                "addonid" = "$addon_id"
                "properties" = @("version"
                    "name"
                    "enabled")
            }
        }

        $json_str = convertTo-Json -InputObject $json_text -compress
        try
        {
            $json_response = Get_Queue_Request $json_str
            if ($null -eq $json_response)
            {
                # Write-Log "Error occurred, null json_response"
                $json_response = $null
            }
            # Write-Log "json_request: $( Format-Table -InputObject $json_text )"
            # Write-Log "json_response: $( Format-Table -InputObject $json_response )"
        }
        catch
        {
            Write-Log "Exception getting json_response"
            Write-Log "$_.Exception.Message"
            $json_response = $null
        }

    }
    PROCESS
    {
        # Basic result of addons.getaddondetails
        #
        #if 'addon' not in data['result']:
        #            return False
        #        if 'enabled' not in data['result']['addon']:
        #            return False
        #        return data['result']['addon']['enabled']

        # Create Hashtable of addon information. The key is the addon id and the value is a Hashtable
        # of: addonid,

        try
        {
            # Write-Log "PROCESS json_response: $json_response"

            if ($null -ne $json_response)
            {
                $result = $( $json_response.result )
                $addon_dict = $( $result.addon )
                $addon_dict2 = $( $addon_dict )

                $addon_id = $( $addon_dict2.addonid )
                $enabled = $False
                if ($( $addon_dict2.enabled ) -eq 'True')
                {
                    $enabled = $True
                }
                $name = $( $addon_dict2.name )
                $version = $( $addon_dict2.version )
                $type = $( $addon_dict2.type )
                # Write-Log "addon_id: $addon_id enabled: $enabled version: $version"
            }
        }
        catch
        {
            Write-Log "In Get_Addon_Details: $_.Exception.Message"
            $json_response = $null
        }
    }

    END
    {
        if ($null -eq $json_response)
        {
            $addon_dict = $null
        }
        else
        {
            try
            {
                $addon_dict = @{
                    addon_id = "$addon_id"
                    enabled = $enabled
                    name = "$name"
                    version = "$version"
                    type = "$type"
                }
            }
            catch
            {
                Write-Log "In Get_Addon_Details: $_.Exception.Message"
                $addon_dict = $null
            }
        }
        Write-Log "Exiting Get_Addon_Details"
        #  Format-Table -InputObject $addon_dict | Out-String | Write-Host
        return $addon_dict
    }
}

Function Enable_Addon
{
    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $true)]
        [string]    $addon_id
    )

    BEGIN
    {
        # Write-Log "In websocket Enable_Addon"

        # DEBUG: Sending message {"method":"Addons.SetAddonEnabled","params":{"addonid":"repo.fbacher","enabled":true},"id":1,"jsonrpc":"2.0"}
        # $enable_tts_rpc = '{"id": 0, "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "service.xbmc.tts", "enabled":true}}'

        # '{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": ' \
        # '{ "addonid": "service.kodi.tts","enabled":%s}, "id": 1 }'

        $json_text = @{
            jsonrpc = "2.0"
            id = 1
            method = "Addons.SetAddonEnabled"
            params = @{
                addonid = "$addon_id"
                enabled = $True
            }
        }

        $json_str = (convertTo-Json -InputObject $json_text -compress)
        $json_response = (Get_Queue_Request $json_str)
        # Write-Log "json_request: ($json_str | Format-Table)"
        # Write-Log "json_response: ($json_response  | Format-Table )"
    }
    PROCESS
    {
        # Basic result of addons.setenabled:
        #    '{"id":"Addon.Details","jsonrpc":"2.0","result":{"addons":[{"addonid":"audioencoder.kodi.builtin.aac"...}
        #  relevant Properties: label, addonid, broken, dependencies

        # Create Hashtable of addon information. The key is the addon id and the value is a Hashtable
        # of: addonid,

        $result = $( $json_response.result )
        # Write-Log "Addons.SetAddonEnabled: ($result | Format-Table)"
        $addon_list = $( $result.addon )
        $addon_dict = @{ }
        foreach ($addon_dict in $addon_list)
        {
            # $formatted = Format-Table -InputObject $addon_dict | Out-String | Write-Host
            #  Write-Debug "addon_dict: $formatted"
            $key = $( $addon_dict.addonid )
            $addon_dict[$key] = $addon_dict
        }
        if ($True)
        {
            foreach ($key in $addon_dict.keys)
            {
                Write-Log "key: $key "
                Write-Log "value: $( $addon_dict[$key] )"
                Write-Log "addon-id: $( $( $addon_dict[$key] ).addonid )"
            }
        }
        return $addon_dict
    }

    END
    {
        # Write-Log "Exiting Enable_Addon"
    }
}

Function Application_Quit
{
    BEGIN
    {
        # Write-Log "In websocket Application_Quit"
    }
    PROCESS
    {
        # curl -X POST -H "content-type:application/json" http://kodi:kodi@127.0.0.1:8080/jsonrpc -d {\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"Application.Quit\"}

        $json_text = @{
            jsonrpc = "2.0"
            id = 1
            method = "Application.Quit"
        }

        $json_str = (convertTo-Json -InputObject $json_text -compress)
        $ignore = (Get_Queue_Request $json_str $False)
    }

    END
    {
        # Write-Log "Exiting Application_Quit"
    }
}
