#REQUIRES -Version 5.1

param([string]    $todo = "Get_Kodi_Location", [switch]    $recurse = $false)
. "$env:homepath/tmp/websocket.ps1"

function Pass_Parameters
{
    Param ([hashtable]$NamedParameters)
    return ($NamedParameters.GetEnumerator()|%{ "-$( $_.Key ) `"$( $_.Value )`"" }) -join " "
}

$Global:Test = $False

# Self-elevate the script if required
if (-not $Global:Test)
{
    if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]'Administrator'))
    {
        if ([int](Get-CimInstance -Class Win32_OperatingSystem | Select-Object -ExpandProperty BuildNumber) -ge 6000)
        {
            $CommandLine = "-File `"" + $MyInvocation.MyCommand.Path + "`" " + (Pass_Parameters $MyInvocation.BoundParameters) + " " + $MyInvocation.UnboundArguments
            Start-Process -FilePath PowerShell.exe -Verb Runas -ArgumentList $CommandLine
            Exit
        }
    }
}
$Global:Trace_Entry_Exit = $True
$Global:Trace_Debug = $True

Write-Debug "Elevated Privilege"
$Global:LOG = 'c:/Users/fbacher/tmp/ps.txt'
rm "$Global:LOG"
Start-Transcript -Path $Global:LOG -Append
$Global:Transcript = "$Global:LOG"

$DebugPreference = 'Continue'
# $DebugPreference = 'SilentlyContinue'
foreach ($key in $MyInvocation.BoundParameters.keys)
{
    Write-Debug -Message "key: $key value: $MyInvocation.BoundParameters[$key]"
}

Function Get_Kodi_Location
{
    # Look for Kodi instances on $PATH as well as Program Files/*/kodi.exe
    # Collect version information and have user choose which to use, or to install
    # a fresh copy.
    BEGIN {
        Write-Debug -Message "Entering Get_Kodi_Location"
        #  Start-Sleep -Seconds 5.0
        #  $candidates = [ordered]@{ }
        # Get map of candidates[<installed_path>, "version"]
        $candidates_wrapper = [ordered]@{ }
        $candidates_wrapper = (Get_Installed_Kodis)  # List of one element
        $installed_info = [System.Collections.Generic.List[System.Collections.Hashtable]]::new()
        $count = 0
        foreach ($key in $candidates_wrapper.keys)
        {
            $version = "$( $candidates_wrapper[$key] )"
            # Write-Log "Path $key Version: $version"
            $compatible = $False
            #
            # TODO: WHAT TO DO ABOUT ALPHAs and Betas?
            # Probably convert 21.3.2.alpha 1 as something like 21.3.2.0.1,
            #          and 21.3.2.beta 1 as something like 21.3.2.1
            # Example
            $split_ver = [System.Collections.Generic.List[string]]::new()
            $temp = $version -Split '[.]', 3
            $split_ver.AddRange($temp)

            # Write-Log "Version: $version split_ver: $split_ver"
            if ($split_ver.count -lt 2)
            {
                # Write-Log "split_ver.count: $split_ver count $( $split_ver.count ) Skipping"
                continue
            }
            if ($split_ver.count -lt 3)
            {
                $split_ver.add('0')
            }
            $major_ver = [int]($split_ver[0])
            $numeric_ver = [int]($major_ver * 10000) + ($minor_ver * 100) + $sub_ver
            # Write-Log "split_ver: $split_ver Major_ver: $major_ver"
            if ([int]$major_ver -lt 20)
            {
                # Write-Log "Version NOT compatible with this TTS Version $version"
            }
            else
            {
                # Write-Log "Version IS compatible with TTS Version: $version"
                $compatible = $True
            }
            $ver_info = @{
                path = "$key"
                version = "$version"
                numeric_ver = $numeric_ver
                compatible = $compatible
            }
            $installed_info.add($ver_info)
            $count += 1
        }
        $installed_info.GetEnumerator() | Sort-Object -Property { $_.numeric_ver } -OutVariable Sorted | Out-Null

        if ($count -gt 0)
        {
            $title = 'TTS Compatible Kodi Installations Found'
            $question = 'Select the installation to use for TTS'

            $Sorted = $( $Sorted )
            $choices = New-Object Collections.ObjectModel.Collection[Management.Automation.Host.ChoiceDescription]
            $choice = -1
            # Write-Log "Sorted: $Sorted"
            # Format-Table -InputObject $Sorted
            foreach ($item in $Sorted)
            {
                $version = $( $item["version"] )
                $path = $( $item['path'] )
                $compatible = $( $item["compatible"] )
                if ($compatible)
                {
                    # Write-Log "Version IS compatible with this TTS Version $version)"
                    $choice += 1
                    $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList "&${choice} Kodi $version located at $path`n"))
                }
                else
                {
                    # Write-Log "Version IS NOT compatible with TTS Version: $version"
                }
            }
            $choice += 1
            $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList "&${choice} Install latest Kodi at: $Global:Kodi_Program_Default_Path`n"))
            $decision = $Host.UI.PromptForChoice($title, $question, $choices, $choice)
            # $choice is index to default (install new Kodi and TTS)
            $install_kodi = $False
            if ($decision -lt $choice)
            {
                # Use existing Kodi installation. Install/Reinstall TTS and requesets.
                try
                {
                    $ver_info = $Sorted[$decision]
                    $Global:Kodi_Install_Version = $( $ver_info["version"] )
                    $Global:Kodi_Install_Path = $( $ver_info['path'] )
                    $Global:TTS_Remove_Settings = $True
                    $Global:TTS_Remove_Cache = $True
                    $Global:TTS_Reset_Keymap = $True

                    Write-Log "Selected kodi version: $Global:Kodi_Install_Version, Path: $Global:Kodi_Install_Path"
                    Write-Log "Using existing Kodi. (Re-)Installing Kodi-TTS and any dependencies."
                    #  TODO: Check for existance of TTS in userdata and prompt user what to do about it.
                    #  Write-Log "ALL TTS Settings, Configuration and Data will be removed."
                }
                catch
                {
                    Write-Log "Exception caught in Get_Kodi_Location. Installation halted."
                    Write-Log $_.Exception.Message
                    return
                }
            }
            else
            {
                $install_kodi = $True
                $Global:Kodi_Install_Version = "$Global:Kodi_Program_Default_Version"
                $Global:Kodi_Install_Path = "$Global:Kodi_Program_Default_Path"
                $Global:TTS_Remove_Settings = $True
                $Global:TTS_Remove_Cache = $True
                $Global:TTS_Reset_Keymap = $True
                Write-Log "Installing latest Kodi ($Global:Kodi_Install_Version) in path: $Global:Kodi_Install_Path"
            }
        }
        $Global:Install_Kodi = $install_kodi
    }

    PROCESS {
        If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
        {
            Write-Log "Script does NOT have admin privilege in Get_Kodi_Location"
        }
    }

    END {
        Trace_Entry_Exit "Exiting Get_Kodi_Location"
    }
}
Function Review_TTS_Settings
{
    # Determine which, if any, TTS Settings to purge
    BEGIN {
        Trace_Entry_Exit "Entering Review_TTS_Settings"
        $kodi_proc_info = Start_kodi
    }
    PROCESS
    {
        $addon_details = Get_Addon_Details "service.kodi.tts"
        # Write-Log "addon_details: [$addon_details]"
        if ($null -eq $addon_details)
        {
            Write-Log "service.kodi.tts NOT installed."
        }
    }
    END
    {
        Trace_Entry_Exit "Exiting Review_TTS_Settings"
    }
}

Function Get_Addon_Images
{
    # Downloads images for addons.
    BEGIN {
        Trace_Entry_Exit "Entering Get_Addon_Images"
    }
    PROCESS {
        # Kodi needs to be running in order to determine if addon is already installed
        $kodi_proc_info = Get_Kodi_Process_Info
        if (-not $kodi_proc_info.kodi_running)
        {
            #  Write-Log "About to run $Global:Kodi_Install_Path"
            $kodi_proc_info = Start_kodi "$Global:Kodi_Install_Path"
            if (-not $kodi_proc_info.kodi_running)
            {
                Write-Log "An error occurred while starting Kodi. Exiting"
                exit
            }
        }
        # Determine which addons need to be downloaded
        foreach ($addon_id in $Global:download_sources.keys)
        {
            $addon_installed = $False
            # Get_Addon_Details returns $null when addon_id not found (i.e. not yet copied over to
            # addons directory).
            $addon_details = Get_Addon_Details "$addon_id"
            if ($null -ne $addon_details -and $addon_details['enabled'])
            {
                $Global:installed_state[$addon_id] = $True
            }
            else
            {
                Download_Image "$addon_id"
                $Global:installed_state[$addon_id] = $False
            }
        }
    }

    END {
        Trace_Entry_Exit "Exiting Get_Addon_Images"
    }
}

Function Install_Images
{
    # Installs the downloaded images, as required.
    # First, non-Kodi applications, such as mpv (audio player) are installed, if needed.
    # These are installed first since TTS may depend upon them (such as Google TTS must have an mpv
    # player.
    BEGIN {
        Trace_Entry_Exit "Entering Install_Images"
    }

    PROCESS {

        # (Re-)Configure TTS settings before starting it
        Configure_TTS
        Install_TTS_Images
    }

    END {
        Trace_Entry_Exit "Exiting Install_Images"
    }
}

Function Get_Installed_Kodis
{
    # Gather the location and version of the installed Kodi executables.
    # See Get_Kodi_Location.

    # [CmdletBinding()]
    # Param declarations
    #  [OutputType([ordered])]  # Type ignored by code, more or less a comment.

    BEGIN {
        Write-Log "In Get_Installed_Kodis"
        # Search_Paths:
        #    Key is path as a string (C:\Program Files\Fred\Ethyl)
        #    Value is list of folders making up path ["C:", "Program Files", "Fred", "Ethyl"]
        $Search_Paths = [ordered]@{ }

        $candidates = [ordered]@{ }
        $System_Drive = $env:SystemDrive
        $paths = $( $Global:PROGRAM_FILES + ';' + $env:PATH ) -split ';'
        # Write-Log "paths: $paths"

        foreach ($path in $paths)
        {
            # Write-Log "PATH: $path"
            try
            {
                if (-not "$path")
                {
                    continue
                }
                # Write-Log "About to Resolve-Path LiteralPath $path"
                $path = Resolve-Path -LiteralPath "$path" -ErrorAction SilentlyContinue
                if (-not "$path")
                {
                    continue
                }
                $is_absolute = Split-Path -Path "$path" -IsAbsolute
                if (Test-Path -LiteralPath "$path")
                {
                    # Write-Log "Test-Path Passes: $path"
                }
                else
                {
                    continue
                }
            }
            catch
            {
                Write-Log "Exception for path: $path"
                Write-Log $_.Exception.Message
                continue
            }
            # Write-Log "path: $path"

            if ( $Search_Paths.Contains("$path"))
            {
                # Write-Log "Ignoring duplicate path: $path"
            }
            else
            {
                # Write-Log "Adding path $path"
                try
                {
                    $path = Resolve-Path -LiteralPath "$path"
                    if (-not $path)
                    {
                        continue
                    }
                    $is_absolute = Split-Path -Path "$path" -IsAbsolute
                    $is_file = Test-Path -LiteralPath "$path" -PathType Leaf
                    # Write-Log "$path is_file: $is_file"
                }
                catch
                {
                    Write-Log "Exception for path: $path"
                    Write-Log $_.Exception.Message
                    continue
                }
                # Convert the file path into an a arraylist from the leaf back to the root
                $expanded_path = [System.Collections.Generic.List[string]]::new()
                $sub_path = $path
                while ($sub_path)
                {
                    # Write-Log "sub-path: $sub_path"
                    try
                    {
                        $name = (get-item $sub_path -Force).PSChildName
                        $expanded_path.insert(0, $name)
                        $parent_path = (get-item $sub_path -Force).PSParentPath
                    }
                    catch
                    {
                        Write-Log "Exception building path list: $sub_path"
                        Write-Log $_.Exception.Message
                        $parent_path = ""
                    }
                    $sub_path = $parent_path
                }
                # Write-Log "Adding search_path: key, expanded_path: $path $expanded_path"
                # foreach ($key in $searchPaths.keys)
                # {
                #    Write-Log ("key: $key value: $searchPaths[$key]")
                # }
                $Search_Paths[$path] = $expanded_path
            }
        }
        # Throw away redundant paths. A Path is redundant if it is a child of another path.
        # Compare each path with every other path, choosing the shortest path that includes
        # the first path. Repeat with each path.
        for ($i = 0; $i -lt $Search_Paths.Count; $i++)
        {
            $key = ([array]$Search_Paths.Keys)[$i]
            if ($Search_Paths[$key]) # Not deleted
            {
                $shortest_key = $key
                for ($j = $i + 1; $j -lt $Search_Paths.Count; $j++)
                {
                    $other_key = ([array]$Search_Paths.Keys)[$j]
                    if ($Search_Paths[$other_key]) # Not deleted
                    {
                        $max_compare = [math]::min($Search_Paths[$key].Count, $Search_Paths[$other_key].Count)
                        # Write-Log "max_compare: $max_compare"
                        if ($max_compare -eq 0)
                        {
                            $overlapping = $false
                        }
                        else
                        {
                            $overlapping = $true
                        }
                        $value = $Search_Paths[$key]
                        $other_value = $Search_Paths[$other_key]
                        for ($f = 0; $f -lt $max_compare; $f++)
                        {
                            if ($value[$f] -ne $other_value[$f])
                            {
                                # Paths diverge before starting point of search for either
                                # tree has been reached
                                $overlapping = $false
                                # Write-Log "not overlapping value, other_value:  $value $other_value"
                                break
                            }
                        }
                        if ($overlapping)
                        {
                            # Throw away the longest path since it is contained by the shortest path
                            if ($max_compare -ieq $Search_Paths[$key].Count)
                            {
                                # Write-Log "overlapping, deleting other"
                                # Write-Log "$value $other_value"
                                # Write-Log "$key $other_key"
                                $Search_Paths[$other_key] = $null
                            }
                            else
                            {
                                # Write-Log "overlapping, deleting key"
                                # Write-Log "$value $other_value"
                                # Write-Log "$key $other_key"
                                $Search_Paths[$key] = $null
                            }
                        }
                    }
                }
            }
        }
        # Purge all entries with $null values
        $keys_to_delete = [System.Collections.Generic.List[string]]::new()
        # Write-Log "keys to delete: $keys_to_delete"

        foreach ($key in $Search_Paths.Keys)
        {
            if (-not $Search_Paths[$key])
            {
                Write-Log "Deleting key: $key"
                $keys_to_delete.Add($key)
            }
            else
            {
                # Write-Log "Keeping key: $key value: $($Search_Paths[$key])"
            }
        }

        foreach ($key in $keys_to_delete)
        {
            # Write-Log "Deleting key: $key"
            try
            {
                $Search_Paths.Remove($key)
            }
            catch
            {
                Write-Log "Ignoring Exception on delete: $_.Exception.Message"
            }
        }
    }

    PROCESS {
        try
        {
            Write-Log "In Get_Installed_Kodis Version"

            # Write-Log "Search_Paths.keys: $( $Search_Paths.Keys )"
            foreach ($key in $Search_Paths.Keys)
            {
                # Write-Log "key: $key"
                $path = $key
                $expanded_path = $Search_Paths[$key]
                # Write-Log "path: $path"
                # Get-ChildItem -Path C:\ -Include *.doc,*.docx -File -Recurse -ErrorAction SilentlyContinue
                # Get-Childitem -Path C:\Users, L:\HSG, X:\Whoops\Not\This\One -Include HSG*.doc? -Recurse
                $cands = Get-ChildItem -Path $path -File -Recurse -ErrorAction SilentlyContinue -Force -Depth 2 -Filter "Kodi.exe" | %{ $_.FullName }
                foreach ($cand_path in $cands)
                {
                    # Write-Log "cand_path: $path cand: $cand_path"
                    if (-not $cand_path)
                    {
                        # Write-Log "Candidate is null"
                        continue
                    }
                    else
                    {
                        try
                        {
                            $fs_path = Resolve-Path -Path "$cand_path"
                            $is_absolute = Split-Path -Path "$fs_path" -IsAbsolute
                            if ($is_file = Test-Path -LiteralPath "$fs_path" -PathType Leaf)
                            {
                                # Write-Log "Hi 2"
                                # Write-Log "is_file: $fs_path"
                            }
                            else
                            {
                                $is_file = $False
                            }
                        }
                        catch
                        {
                            # Write-Log "Hi 3"
                            Write-Log "Exception for path: $cand_path"
                            Write-Log $_.Exception.Message
                            continue
                        }
                        # Convert the file path into an a arraylist from the leaf back to the root
                        $expanded_path = [System.Collections.Generic.List[string]]::new()
                        $sub_path = $fs_path
                        while ($sub_path)
                        {
                            # Write-Log "Candidate path: $fs_path"
                            try
                            {
                                $name = (get-item $sub_path -Force).PSChildName
                                $expanded_path.insert(0, $name)
                                $parent_path = (get-item $sub_path -Force).PSParentPath
                            }
                            catch
                            {
                                Write-Log "Exception building path list from: $fs_path"
                                Write-Log $_.Exception.Message
                                $parent_path = ""
                            }
                            $sub_path = $parent_path
                        }
                        try
                        {
                            # To get Version (from linux):
                            # fbacher@smeagol$ /usr/local/lib/kodi/kodi.bin -v
                            # Kodi Media Center 21.2 (21.2.0) Git:20250115-d1a1d48c3c-dirty
                            # Copyright (C) 2005-2025 Team Kodi - http://kodi.tv
                            #
                            # /usr/local/lib/kodi/kodi.bin -v|awk '/Git/ {print( $5)}'
                            # Gives: (21.2.0)
                            #
                            # From Windows:
                            # acher@winbiten ~/tmp
                            #  $ /cygdrive/c/"Program Files"/kodi20/kodi.exe -v
                            #  Kodi Media Center 20.5 (20.5.0) Git:20240303-4b95737efa
                            #  Copyright (C) 2005-2021 Team Kodi - http://kodi.tv

                            # Write-Log "Hi 5"
                            # Write-Log "fs_path: $fs_path"
                            $x = & cmd.exe /q /v /c "$fs_path" -v
                            #  Write-Log "result x: $x"
                            if (-not $x)
                            {
                                # Write-Log "x is null '$x'"
                                continue
                            }
                            $version = $x[0] -replace '(^.*Center\s)([1-9][0-9][.][0-9])(\s.*$)', '$2'
                            # Write-Log "Version: $Version"
                            $candidates[$fs_path] = $version
                        }
                        catch
                        {
                            Write-Log $_.Exception.Message
                        }
                    }
                }
            }
        }
        catch
        {
            Write-Log "Exception"
            Write-Log $_.Exception.Message
            # Write-Error $_.Exception.Message
            # Write-Log "Exception ocurred in Get_Installed_Kodis"
        }
        # foreach ($key in $candidates.keys)
        # {
        # Write-Log "Path $key Version: $( $candidates[$key] )"
        # }
        return (,$candidates)
    }
    END {
        Trace_Entry_Exit "Exiting Get_Installed_Kodis"
    }
}

Function Get_Kodi_Image
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Kodi_Image"
        $kodi_exe_out = Join-Path "$Global:workingDir" "kodi_installer.exe"

        # Delete Temp download file (kod_exe_out)
        $installer_file_name = Split-Path -Path "$kodi_exe_out" -Leaf
        Prepare_Working_Dir -delete_child $True -child "$installer_file_name"
    }

    PROCESS
    {
        # Write-Log "About to download $Global:Kodi_url"
        Write-Log "Downloading $Global:Kodi_url to $kodi_exe_out"
        (New-Object System.Net.WebClient).DownloadFile("$Global:Kodi_url", "$kodi_exe_out")

        # Write-Log "Download complete"
        return
    }

    END
    {
        Trace_Entry_Exit "Exiting Get_Kodi_Image"
    }
}

Function Get_Kodi_Install_State
{
    # Stop any running Kodi
    # Start desired version
    # Determine if Kodi is installed, at what version and if broken
    # Also determine if repo.fbacher is installed, at what version, if enabled and if broken
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Kodi_Install_State"
    }

    PROCESS
    {
        try
        {
            # Write-Log "Checking to see if 'Kodi' is running"
            $kodi_proc_info = Get_Kodi_Process_Info
            # $value = ($Kodi_proc_info.Keys | foreach { "$_ $( $Kodi_proc_info[$_] )" }) -join "|"
            # Write-Log "Kodi_proc_info: $value"
            $kodi_running = $kodi_proc_info.kodi_running
            $kodi_tts_up_to_date = $False
            $kodi_path = $kodi_proc_info.kodi_running_path
            $kodi_proc_id = $kodi_proc_info.kodi_proc_id
            if ($kodi_running)
            {
                # Write-Log "Script thinks that kodi is running: $kodi_running" $True
                # Write-Log "kodi_path: $kodi_path Install_path: $Global:Kodi_Install_Path"
                if ("$kodi_path" -ne "$Global:Kodi_Install_Path")
                {
                    Write-Log "Stopping incorrect Kodi instance from running."
                    Write-Log "Current Kodi path: $kodi_path Should be $Global:Kodi_Install_Path"
                    $kodi_proc_info = Stop_Kodi $kodi_proc_info
                    $kodi_running = $kodi_proc_info.kodi_running
                    $kodi_tts_up_to_date = $False
                    $kodi_path = $kodi_proc_info.kodi_running_path
                }
                else
                {
                    # Write-Log "Correct instance of Kodi is running"
                }
            }
        }
        catch
        {
            Write-Log $_.Exception.Message
        }

        if (-not $kodi_running)
        {
            #  Write-Log "About to run $Global:Kodi_Install_Path"
            $kodi_proc_info = Start_kodi "$Global:Kodi_Install_Path"
            if (-not $kodi_proc_info.kodi_running)
            {
                Write-Log "An error occurred while starting Kodi. Exiting"
                exit
            }
        }
        try
        {
            # Verify kodi image matches the version we expect

            $kodi_path = $kodi_proc_info.kodi_running_path
            # Write-Log "kodi_running_path: $kodi_path"
            $x = & cmd.exe /q /v /c "$kodi_path" -v
            # Write-Log "result x: $x"
            if (-not $x)
            {
                Write-Log "x is null"
                continue
            }
            $kodi_version = $x[0] -replace '(^.*Center\s)([1-9][0-9][.][0-9])(\s.*$)', '$2'
            # Write-Log "kodi_version: $kodi_version"
        }
        catch
        {
            Write-Log $_.Exception.Message
            # Write-Error $_.Exception.Message
        }
        if ($kodi_version -ne $Global:Kodi_Install_Version)
        {
            # We are hosed. We restarted the path to Kodi that should be for the
            # correct version, but nope. Report the issue and let user worry about.
            try
            {
                Write-Log "Expected Kodi version to be $Global:Kodi_Install_Version, but is $kodi_version"
                Write-Log "Stopping Kodi. User needs to resolve problem and then restart this script."
                $kodi_proc_info = Stop_Kodi $kodi_proc_info
                $kodi_running = $False
            }
            catch [ObjectNotFound]
            {
                Write-Log "Kodi should be running, but is not"
                Write-Log $_.Exception.Message $True
                $kodi_running = $False
                exit
            }
            catch
            {
                $kodi_running = $False
                Write-Log $_.Exception.Message
                Write-Log "An error occurred while trying to stop Kodi"
                Write-Log "Please stop manually, and run again"
                exit
            }
            exit
        }
    }

    END
    {
        Trace_Entry_Exit "Exiting Get_Kodi_Install_State"
    }
}

<#
Function Get_Kodi_Version
{
    # Simply extracts the version from the kodi executable at the given path

    param([Parameter(Position = 0, Mandatory = $False)]
        [string]  $kodi_exec_path = "$Global:Kodi_Install_Path"
    )

    BEGIN
    {
        # Trace_Entry_Exit "Entering Get_Kodi_Version" #  Global:Kodi_install_path: $Global:Kodi_Install_Path"
    }
    PROCESS
    {
        try
        {
            # Verify kodi image matches the version we expect

            # Write-Log "kodi_running_path: $kodi_exec_path"
            $x = & cmd.exe /q /v /c "$kodi_exec_path" -v
            # Write-Log "result x: $x"
            if (-not $x)
            {
                # Write-Log "x is null: $x kodi_exec_path: $kodi_exec_path"
                continue
            }
            $kodi_version = $x[0] -replace '(^.*Center\s)([1-9][0-9][.][0-9])(\s.*$)', '$2'
            # Write-Log "kodi_version: $kodi_version"
        }
        catch
        {
            Write-Log $_.Exception.Message
            Exit
        }
    }
    END
    {
        # Trace_Entry_Exit "Exiting Get_Kodi_Version version: $kodi_version"
        return $kodi_version
    }
}
#>

Function Start_Kodi
{
    # Starts Kodi if needed
    #   Restart if version or path is incorrect
    #           OR if $restart is $True
    # When starting, delay $sleep seconds before returning

    # Returns HashMap with status:
    #    $result =  @{
    #            kodi_running = <switch>
    #            kodi_running_path = <string>
    #            kodi_proc_id = <string>
    #            kodi_version = <version string>
    #           }

    param([Parameter(Position = 0, Mandatory = $False)]
        [string]  $kodi_exec_path = "$Global:Kodi_Install_Path",
        [Parameter(Position = 1, Mandatory = $False)]
        [String] $expected_version = "$Global:Kodi_Install_Version",
        [Parameter(Position = 2, Mandatory = $False)]
        [int] $window_style = $Global:WindowStyle_Hidden,
        [Parameter(Position = 3, Mandatory = $False)]
        [Double] $sleep = $Global:Startup_Delay,
        [Parameter(Position = 4, Mandatory = $False)]
        [switch] $restart = $False
    )
    # Start_Kodi -FilePath "$Kodi_exec_Path" -WindowStyle @window_style -Sleep $Global:Startup_Delay

    BEGIN
    {
        Trace_Entry_Exit "Entering Start_Kodi kodi_exec_path: $kodi_exec_path Delay: $sleep"
    }

    PROCESS
    {
        try
        {
            # Write-Log "Checking to see if 'Kodi' is running"
            $kodi_proc_info = Get_Kodi_Process_Info
            # Write-Log "Kodi_proc_info"
            # Format-Table -InputObject $Kodi_proc_info | Out-String | Write-Host
            if ($kodi_proc_info.kodi_running)
            {
                Write-Log "Kodi already running"
                if ($restart)
                {
                    Write-Log "Restarting Kodi on request"
                }
                elseif ($kodi_proc_info.kodi_path -ne "$kodi_exec_path")
                {
                    Write-Log "Stopping incorrect or unknown Kodi instance from running."
                    Write-Log "Current Kodi path: $kodi_proc_info.kodi_path Should be $kodi_exec_path"
                    $kodi_proc_info = Stop_Kodi $kodi_proc_info
                }
            }
        }
        catch
        {
            Write-Log $_.Exception.Message
            Write-Log "Please correct the problem and rerun"
            Exit
        }

        if (-not $kodi_proc_info.kodi_running)
        {
            # Write-Log "Starting $kodi_exec_path"
            try
            {
                Start-Process -FilePath "$kodi_exec_path" -WindowStyle $window_style
                (Start-Sleep -Seconds $sleep)

                Write-Log "Started Kodi path: $kodi_proc_info.kodi_exec_path Sleep: $sleep"
                $kodi_proc_info = Get_Kodi_Process_Info
            }
            catch
            {
                Write-Log "Exception while starting $kodi_exec_path"
                Write-Log $_.Exception.Message
                $kodi_proc_info = @{
                    kodi_running = $False
                    kodi_running_path = $kodi_exec_path
                    kodi_proc_id = $Null
                }
            }
            if (-not $kodi_proc_info.kodi_running)
            {
                Write-Log "An error occurred while starting Kodi at $kodi_exec_path. Exiting"
                exit
            }
        }
    }

    END
    {
        Trace_Entry_Exit "Exiting Start_Kodi"
        return $kodi_proc_info
    }
}

Function Get_Addon_State
{
    # Determine if the given addon is installed and enabled
    # Starts Kodi, as needed.

    param([Parameter(Position = 0, Mandatory = $True)]
        [string]  $addon_id
    )
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Addon_State"

        # If Kodi is not running, exit with error
        $kodi_running = $False
        $running_path = $null
        try
        {
            Write-Log "Checking to see if 'Kodi' is running"
            $props = Get-Process -Name "kodi" -ErrorAction SilentlyContinue | Select-Object Path
            $running_path = $props.Path
            Write-Log "Kodi running_path: $running_path Install Path: $Global:Kodi_Install_Path"
            if ("$running_path" -eq "$Global:Kodi_Install_Path")
            {
                $kodi_running = $True
            }
        }
        catch [ObjectNotFound]
        {
            Write-Log "ObjectNotFound exception"
            Write-Log $_.Exception.Message $True
        }
        catch
        {
            Write-Log $_.Exception.Message
        }
        if (-not $kodi_running)
        {
            Write-Log "Kodi is not running. Exiting."
            Exit
        }

        $addons_dict = Get_Addon_Info "$addon_id"
        $addon_installed = $False
        if ($addons_dict -Contains "$addon_id")
        {
            $addon_installed = $True
            $addon_enabled = $addons_dict["$addon_id"]['enabled']
            Write-Debug "$addon_id enabled"
        }
    }
    END
    {
        Trace_Entry_Exit "Exiting Get_Addon_State addon: $addon_id is $state"
    }
}

Function Get_Kodi_Process_Info
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Kodi_Process_Info"
        $kodi_running = $False
        $kodi_running_path = $null
        $kodi_proc_id = $null
    }
    PROCESS
    {
        try
        {
            If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
            {
                Write-Log "Script does NOT have admin privilege in Get_Kodi_Location"
            }
            # It is a bit complicated to get two properties in one call (efforts so far yield weird results).
            $kodi_proc_id = Get-Process -Name "kodi" -ErrorAction SilentlyContinue | Select-Object -expand ID
            $kodi_running_path = Get-Process -Name "kodi" -ErrorAction SilentlyContinue | Select-Object -expand Path

            if ($kodi_proc_id)
            {
                # Write-Log "KODI IS RUNNING"
                Write-Log "kodi_proc_id: $kodi_proc_id"
                Write-Log "Kodi running_path: $kodi_running_path Install Path: $Global:Kodi_Install_Path"
                # Write-Log "Setting kodi_running to True"
                $kodi_running = $True
            }
        }
        catch [ObjectNotFound]
        {
            Write-Log "ObjectNotFound exception"
            Write-Log $_.Exception.Message $True
        }
        catch
        {
            Write-Log $_.Exception.Message
        }
    }
    END
    {
        $result = @{
            kodi_running = $kodi_running
            kodi_running_path = $kodi_running_path
            kodi_proc_id = $kodi_proc_id
        }
        Trace_Entry_Exit "Exiting Get_Kodi_Process_Info"
        # Write-Log "result formatted: $( $result | Format-List |out-string ) )"
        return $result
    }
}

Function Stop_Kodi
{
    # Stops any running Kodi.
    # Sleeps $Global:Stop_Delay Seconds
    param([Parameter(Position = 0, Mandatory = $true)]
        [hashtable]    $kodi_proc_info
    )
    BEGIN
    {
        Trace_Entry_Exit "Entering Stop_Kodi proc_info:"
    }
    PROCESS
    {
        try
        {
            Application_Quit
        }
        catch
        {
            Write-Log "Exception thrown on Application_Quit."
        }
        try
        {
            $kodi_proc = Get-Process -Name "kodi" -ErrorAction SilentlyContinue
            if (($null -ne $kodi_proc) -and ($null -ne $( $kodi_proc.proc_id )))
            {
                Write-Log "Kodi still running $Global:Stop_Delay seconds after stopping it. Killing it now"
                Stop-Process -InputObject $kodi_proc -ErrorAction SilentlyContinue
                $dead_process = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.HasExited }
                Write-Log "Stopped Kodi: $dead_process"
            }
        }
        # catch [NoProcessFoundForGivenName]
        # {
        #     Write-Log "Kodi not running"
        # }
        catch
        {
            Write-Log $_.Exception.Message
            Write-Log "An error occurred while trying to stop Kodi"
            Write-Log "Please stop manually, and run again"
            exit
        }
    }
    END
    {
        $result = @{
            kodi_running = $False
            kodi_running_path = $null
            kodi_proc_id = $null
        }

        (Start-Sleep $Global:Stop_Delay)
        Trace_Entry_Exit "Exiting Stop_Kodi" $False
        return $result
    }
}

Function Get_TTS_Install_State
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_TTS_Install_State"

        $kodi_proc_info = Get_Kodi_Process_Info
        if (-not $kodi_proc_info.kodi_running)
        {
            Write-Log "Kodi is not running. Exiting."
            Exit
        }
    }

    PROCESS
    {
        $kodi_tts_up_to_date = $False

        # Next, see if the addon is known to kodi (installed, or just known from repository data, etc.).
        # Kodi gives an error if the addon is not in the database. You can't distinguish the reason for
        # the error.

        $kodi_tts_installed = $False
        $kodi_tts_version = $null
        $kodi_tts_enabled = $False
        $addons_dict = Get_Addon_Info
        $repository_installed = $False
        if (-not ($addons_dict -Contains "service.kodi.tts"))
        {
            Write-Debug "service.kodi.tts is not registered in database."
        }
        else
        {
            $addon_details = Get_Addon_Details "service.kodi.tts"
            if (-not $addon_details)
            {
                $kodi_tts_installed = $False
            }
            else
            {
                $kodi_tts_enabled = $addon_details['enabled']
                $kodi_tts_installed = $addon_details['installed']
                $kodi_tts_version = $addon_details['version']
            }
        }
    }

    END
    {
        Write-Debug "TTS enabled: $kodi_tts_enabled installed: $kodi_tts_installed version: $kodi_tts_version"
        $result = @{
            kodi_tts_enabled = $kodi_tts_enabled
            kodi_tts_installed = $kodi_tts_installed
            kodi_tts_version = $kodi_tts_version
        }
        Trace_Entry_Exit "Exiting Get_TTS_Install_State"
        return $result
    }
}

<#
Function Get_Json_Login
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Json_Login"
    }
    PROCESS
    {
        # <setting id="services.webserver">true</setting>
        #    <setting id="services.webserverport" default="true">8080</setting>
        #    <setting id="services.webserverauthentication" default="true">true</setting>
        #    <setting id="services.webserverusername" default="true">kodi</setting>
        #    <setting id="services.webserverpassword">gr8vey</setting>
        #    <setting id="services.webserverssl" default="true">false</setting>
        #  Allow rpc over websocket or tcp locally
        #     <setting id="services.esenabled" default="true">true</setting>
        #  Allow json/rpc over websocket or tcp remotely
        #    <setting id="services.esallinterfaces" default="true">true</setting>
        #
        $Global:Kodi_gui_settings_path
        $save_gui_settings_path = "$Global:Kodi_gui_settings_path".save

        # Are changes required?
        # $kodi_id
        # $kodi_passwd
        # $kodi_port
        # $kodi_auth
        # $kodi_ssl
        Write-Log "Moving $Global:Kodi_gui_settings_path to $save_gui_settings_path"
        Move-Item -LiteralPath "$Global:Kodi_gui_settings_path" -Destination "$save_gui_settings_path"
        $copyParams = @{
            LiteralPath = "\\Server01\Share\Get-Widget.ps1"
            Destination = "\\Server12\ScriptArchive\Get-Widget.ps1.txt"
        }
        Copy-Item @copyParams
        Get-Content -LiteralPath "$Global:Kodi_gui_settings_path"
        Select-String -Path "C:\Logs\WebServer.log" -Pattern "404"
        $content = Get-Content -Path "C:\path\to\your\file.txt"
        $content[2] = "This is the new line."
        Set-Content -Path "C:\path\to\your\file.txt" -Value $content
    }
    END
    {
        Trace_Entry_Exit "Exiting Get_Json_Login"
    }
}
#>

Function Download_Image
{
    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $true)]
        [string]    $Subject_Id
    )
    # Download TTS images from the informal Repository that I have:
    # https://feuerbacher.us/repo/repo/zips/repo.fbacher/repo.fbacher-1.0.0.zip
    # Install the repo into Kodi, then drive the installation from there via json-rpc
    BEGIN
    {
        Trace_Entry_Exit "Entering Download_Image"
        $URL = $Global:download_sources[$Subject_Id]
        $tmp_destination = $Global:download_destination[$Subject_Id]
        $tmp_unzip = $Global:download_unzip[$Subject_Id]
        Write-Log "tmp_unzip: $tmp_unzip Subject: $Subject_Id"
        # $Global:download_destination

        # Write-Log "In Download_Image From $URL To: $tmp_destination"
        # $Global:tts_service_url

        $download_leaf = Split-Path -Leaf "$tmp_destination"
        Prepare_Working_Dir -delete_child $True -child "$download_leaf"
    }

    PROCESS
    {
        try   # TODO: Remove long_path stuff
        {
            # Write-Log "Getting download_parent for: $tmp_destination" $True
            $download_parent = Split-Path -Parent "$tmp_destination"
            # Write-Log "Getting long_path of $download_parent" $True
            $long_path = (Get-Item -LiteralPath "$download_parent").FullName
            # Write-Log "long_path is: $long_path" $True
            Write-Log "Downloading $URL  TO: $tmp_destination" # $True
            Invoke-WebRequest -Uri $URL -OutFile "$tmp_destination"
            Expand-Archive -LiteralPath "$tmp_destination" -DestinationPath "$tmp_unzip"
            Write-Log "tmp_unzip: $tmp_unzip" # $True

            # Write-Log "Download complete" $True
        }
        catch
        {
            Write-Log $_.Exception.Message $True
            Write-Log $error[0].Exception.ToString()
        }
    }

    END
    {
        Trace_Entry_Exit "Exiting Download_Image"
    }
}

Function Get_Optional_Images
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_Optional_Images"
    }

    PROCESS
    {
        $Global:install_mpv = $True
        if (Test-Path "$Global:mpv_install_path")
        {
            Write-Log "mpv_install_path $Global:mpv_install_path exists. Query to replace"
            $title = 'mpv exists'
            $question = 'Reinstall mpv at $Global:mpv_install_path?'

            $choices = New-Object Collections.ObjectModel.Collection[Management.Automation.Host.ChoiceDescription]
            $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList '&Yes'))
            $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList '&No'))

            $decision = $Host.UI.PromptForChoice($title, $question, $choices, 1)
            if ($decision -eq 0)
            {
                try
                {
                    Write-Host 'Removing existing mpv'
                    If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
                    {
                        Write-Log "Script does NOT have admin privilege"
                    }
                    (Remove-Item -Recurse -Force "$Global:mpv_install_path")
                }
                catch
                {
                    Write-Log "Exception caught in Get_Optional_Images whle removing $Global:mpv_install_path"
                    Write-Log $_.Exception.Message $True
                    return
                }
            }
            else
            {
                Write-Host 'Keeping existing mpv'
                $Global:install_mpv = $False
            }
        }
        if ($Global:install_mpv)
        {
            Get_MPV_Images
        }
    }
    END
    {
        Trace_Entry_Exit "Exiting Get_Optional_Images"

    }
}

Function Get_MPV_Images
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Get_MPV_Images"
        # Delete any mpv.zip and unpacked .zip
        $mpv_zip = Split-Path -Leaf "$Global:mpv_zip_target"
        $mpv_tmp_dir = Split-Path -Leaf "$Global:mpv_tmp_install"
        Write-Log "About to delete mpv_zip, mpv_tmp_dir: $mpv_zip $mpv_tmp_dir"
        Prepare_Working_Dir -delete_child $True -child "$mpv_zip"
        Prepare_Working_Dir -delete_child $True -child "$mpv_tmp_dir"
        Write-Log "Just prepared working dir for mpv" # $True
    }

    PROCESS
    {
        Write-Log "Downloading $Global:mpv_url to $Global:mpv_zip_target"
        Write-Log "$Global:mpv_url"
        Write-Log $Global:mpv_zip_target
        Write-Log "$Global:mpv_zip_target"

        #  Trace-Command -Name Metadata, ParameterBinding, Cmdlet -Expression {(New-Object System.Net.WebClient).DownloadFile("$Global:mpv_url", $Global:mpv_zip_target)} -PSHost
        (New-Object System.Net.WebClient).DownloadFile("$Global:mpv_url", $Global:mpv_zip_target)
        Write-Log "mpv download complete."
    }

    END
    {
        Trace_Entry_Exit "Exiting Get_MPV_Images"
    }
}

Function Install_Kodi
{
    # Assumption: Get_Kodi_Image run prior to this.
    # Need to run downloaded kodi_installer.exe with admin privilege.  This installer will
    # present user with dialog to choose where to install kodi.
    BEGIN
    {
        Trace_Entry_Exit "Entering Install_Kodi"
    }

    PROCESS
    {
        Write-Log "About to install Kodi"
        $kodi_installer_path = Join-Path "$Global:workingDir" "kodi_installer.exe"
        Write-Log "kodi_installer_path: $kodi_installer_path"
        try
        {
            $process = Start-Process -FilePath "$kodi_installer_path" -WorkingDirectory "$Global:workingDir" -Wait  *>> $Global:LOG # -PassThru
            Write-Log "Ran kodi_installer rc:  $( $process.ExitCode )"
        }
        catch
        {
            Write-Log $_.Exception.Message $True
        }
    }

    END
    {
        Trace_Entry_Exit "Exiting Install_Kodi"
    }
}

Function Install_3rd_Party_Images
{
    # Install optional mpv, etc.
    # In mpv's case, installation consists of unpacking .zip into $Global:workingDir/mpv_test.
    #
    BEGIN
    {
        Trace_Entry_Exit "Entering Install_3rd_Party_Images"
    }

    PROCESS
    {
        # $updater_script = "updater.bat"
        if (Test-Path "$Global:mpv_tmp_install")
        {
            # Not likeky to have downloaded mpv in tmp dir, but just in case, delete it.
            Write-Log "About to delete $Global:mpv_tmp_install"
            Remove-Item -Recurse -Force "$Global:mpv_tmp_install"
        }

        if ($Global:install_mpv)
        {
            try
            {
                Write-Log "About to Extract mpv.zip $Global:mpv_zip_target to $Global:mpv_tmp_install"
                If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
                {
                    Write-Log "Script does NOT have admin privilege"
                }
                Write-Log "Does $Global:mpv_tmp_install exist?" # $True
                Expand-Archive -LiteralPath "$Global:mpv_zip_target" -DestinationPath "$Global:mpv_tmp_install"
                Write-Log "Copying mpv from $Global:mpv_tmp_install to $Global:mpv_install_path" # $True
                (Copy-Item -Path "$Global:mpv_tmp_install/**/" -Destination "$Global:mpv_install_path" -Recurse)
                Write-Log "Run mpv install script: $Global:mpv_install_path/updater.bat" # $True
                Start-Process -FilePath "$Global:mpv_install_path/updater.bat" -Wait *>> "$Global:LOG"
            }
            catch
            {
                Write-Log "Exception while installing mpv"
                return
            }
        }
        elseif (Test-Path "$Global:mpv_tmp_install")
        {
            # Not likely to have downloaded mpv in tmp dir, but just in case, delete it.
            Write-Log "About to cleanup mpv install by deleting $Global:mpv_tmp_install"
            Remove-Item -Recurse -Force "$Global:mpv_tmp_install"
        }
    }
    END
    {
        Trace_Entry_Exit "Exiting Install_3rd_Party_Images"
    }
}

<#
   Prepares the temp working directory for scratch files.
   The top of the working directory is always $Global:WorkingDir

   Depending on the arguments, the directory and a sub-directory
   can be created or deleted.
#>
Function Prepare_Working_Dir
{
    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $true)]
        [switch]    $create_working_dir = $false, # If True, then create $Global:workingDir, if needed

        [Parameter(Position = 1, Mandatory = $false)]
        [switch]    $delete_working_dir = $false, # If True, then recursively delete $Global:workingDir

        [Parameter(Position = 2, Mandatory = $false)]
        [switch]    $create_subdir = $False, # If True, then create $Global:workingDir/$subdir

        [Parameter(Position = 3, Mandatory = $false)]
        [switch]    $delete_child = $False, # If True, then recursively delete $Global:workingDir/$subdir

        [Parameter(Position = 4, Mandatory = $false)]
        [string]    $child = $null)
    # Specifies the subdir to create or subdir/file  to delete.
    # $child must be a leaf node, or $null

    BEGIN
    {
        Trace_Entry_Exit "Entering Prepare_Working_Dir"
        If ($False)
        {
            Write-Log "create_working_dir: $create_working_dir"
            Write-Log "delete_working_dir: $delete_working_dir"
            Write-Log "create_subdir: $create_subdir"
            Write-Log "delete_child: $delete_child"
            Write-Log "child: $child"
        }
    }

    PROCESS
    {
        try
        {
            $subtree_to_remove = $null
            if ("$delete_working_dir" -eq $True)
            {
                $subtree_to_remove = "$Global:workingDir"
            }
            elseif ("$delete_child")
            {
                if (-not "$child")
                {
                    Write-Log "child argument is null, specify a valid file or folder name"
                    return
                }
            }
            $subtree_to_remove = Join-Path "$Global:workingDir" "$child"
            try
            {
                if (Test-Path $subtree_to_remove)
                {
                    # Write-Log "Deleting: $subtree_to_remove" # $True
                    Remove-Item -Recurse -Force "$subtree_to_remove"
                }
            }
            catch
            {
                Write-Log "Exception occured trying to remove $subtree_to_remove"
                Write-Log $_.Exception.Message $True
            }

            $directory_to_create = $null
            if ($create_working_dir)
            {
                # Write-Log "Creating working dir: $Global:workingDir"
                $directory_to_create = "$Global:workingDir"
            }
            elseif ($create_subdir)
            {
                if (-not "$child")
                {
                    Write-Log "child argument is null, specify a valid file or folder name"
                    return
                }
                # Write-Log "Directory to create: $directory_to_create"
                $directory_to_create = Join-Path "$Global:workingDir" "$child"
            }
            if ($directory_to_create)
            {
                try
                {
                    if (-not (Test-Path $directory_to_create))
                    {
                        # Write-Log "Creating Directory: $directory_to_create" # $True
                        # $long_path = (Get-Item -LiteralPath $download_parent).FullName

                        New-Item -Force -Path "$directory_to_create" -ItemType Directory
                    }
                }
                catch
                {
                    Write-Log "Exception occurred while creating $directory_to_create / $child"
                    Write-Log $_.Exception.Message $True
                }
            }
            [Console]::Out.Flush()
        }
        catch
        {
            Write-Log "Uncaught Exception"
            Write-Log $_.Exception.Message $True
        }
    }

    END
    {
        Trace_Entry_Exit "Exiting Prepare_Working_Dir"
    }
}

function Install_TTS_Images
{
    BEGIN
    {
        Trace_Entry_Exit "Entering Install_TTS_Images"
        $kodi_proc_info = Get_Kodi_Process_Info
        $kodi_proc_info = Stop_Kodi $kodi_proc_info
    }
    PROCESS
    {
        foreach ($addon_id in $Global:installed_state.keys)
        {
            # Write-Log "addon: $addon_id installed: $( $Global:installed_state[$addon_id] )"
            if (-not $Global:installed_state[$addon_id])
            {
                Install_Addon "$addon_id"
            }
        }
    }
    END
    {
        Trace_Entry_Exit "Exiting Install_TTS_Images"
    }
}

function Install_Addon
{
    [CmdletBinding()]
    param([Parameter(Position = 0, Mandatory = $True)]
        [string]    $Subject_Id
    )
    BEGIN
    {
        Trace_Entry_Exit "Entering Install_Addon for $Subject_Id"
        $kodi_proc_info = Get_Kodi_Process_Info
        $kodi_proc_info = Stop_Kodi $kodi_proc_info

        # An addon, such as service.kodi.tts, is packed in a zip that includes its version number (service.kodi.tts-2.3~alpha8.zip).
        # The directory to install (copy to Kodi's addon directory) is at the top level in the zip and DOES NOT have a
        # version number. So for this example, we copy service.kodi.tts from the unzipped folder named service.kodi.tts-2.3~alpha8.

        # The addon is in the top level directory where the addon was unzipped. The
        # directory will have the name of the addon-id

        $tmp_source = Join-Path $Global:download_unzip[$Subject_Id] $Subject_Id

        # Directory to copy the addon to
        $addon_destination = $Global:install_destination[$Subject_Id]
        $tmp_addon_destination = "${addon_destination}.tmp"
        $inst_save = "${addon_destination}.inst_save"
        Write-Log "tmp_source: $tmp_source addon_destination: $addon_destination inst_save: $inst_save"
    }

    PROCESS
    {
        # Copy new addon to proper place
        # Start Kodi
        try
        {
            try
            {
                Write-Log "tmp_addon_destination: $tmp_addon_destination"
                if (Test-Path "$tmp_addon_destination")
                {
                    Write-Log "Deleting: $tmp_addon_destination" # $True
                    Remove-Item -Recurse -Force "$tmp_addon_destination"
                }
                Write-Log "Copying $tmp_source to $tmp_addon_destination -Recurse"
                Copy-Item -LiteralPath "$tmp_source" -Destination "$tmp_addon_destination" -Recurse
            }
            catch
            {
                Write-Log "Exception during Copy-Item of $tmp_source To $tmp_addon_destination. Install FAILED."
                Write-Log ($_.Exception.Message) $True
                Exit
            }
            try
            {
                # Write-Log "Trying to save old version of $Subject_Id"
                if (Test-Path "$inst_save")
                {
                    # Write-Log "Deleting old saved version of $Subject_Id"
                    Remove-Item -Recurse -Force "$inst_save"
                }

                if (Test-Path "$addon_destination")
                {
                    # Write-Log "Saving previously installed addon"
                    Rename-Item -Path "$addon_destination" -NewName "$inst_save"
                }
            }
            catch
            {
                Write-Log "Exception while saving $inst_save. Install FAILED."
                Write-Log $_.Exception.Message $True
                Exit
            }
            try
            {
                if (Test-Path "$addon_destination")
                {
                    Write-Log "Error: $addon_destination should not exist. Install FAILED"
                    Exit
                }
                Rename-Item -Path "$tmp_addon_destination" -NewName "$addon_destination"
                Write-Log "Rename_Item From $tmp_addon_destination TO $addon_destination" # $True
            }
            catch
            {
                Write-Log "Install of $tmp_addon_destination FAILED during rename"
                Write-Log $_.Exception.Message $True
                Exit
            }
            try
            {
                $kodi_proc_info = Start_kodi "$Global:Kodi_Install_Path"
            }
            catch
            {
                Write-Log "Could not start Kodi!"
                Write-Log $_.Exception.Message $True
                Exit
            }
            try
            {
                # Starting Kodi should enable the addon
                $addon_details = Get_Addon_Details "$Subject_Id"
                if (-not $addon_details.enabled)
                {
                    Write-Log "Enabling $Subject_Id"
                    $addon_dict = Enable_Addon "$Subject_Id"
                    (start-sleep -seconds $Global:Enable_Delay)
                    $addon_details = Get_Addon_Details "$Subject_Id"
                }
                if ($addon_details.enabled)
                {
                    Write-Log "Enabled: $Subject_Id"
                }
                else
                {
                    Write-Log "NOT Enabled: $Subject_Id"
                }
            }
            catch
            {
                Write-Log "$Subject_Id NOT Enabled failure: $failures"
                Write-Log $_.Exception.Message $True
                # Exit
            }
        }
        finally
        {
            if (Test-Path "${inst_save}")
            {
                try
                {
                    # Write-Log "Removing temp files"
                    Remove-Item -Recurse -Force "${inst_save}"
                }
                catch
                {
                    Write-Log "Exception while removing ${inst_save}"
                    Write-Log $_.Exception.Message $True
                }
            }
        }
    }
    END
    {
        $kodi_proc_info = Stop_Kodi $kodi_proc_info
        Trace_Entry_Exit "Exiting Install_Addon $Subject_Id"
    }
}

Function Configure_TTS
{
    # Allow user to configure first-use Kodi behavior

    Write-Log "In Configure_TTS"
    $Yes = 1
    $No = 2

    $reset_config = $No
    $config_keymap = $No
    $run_config_gui = $No
    $enable_hint_text = $No
    $enable_help_text = $No
    $enable_extended_help = $No
    $voice_introduction = $No

    Choice /c yn /m "Reset TTS to Default Configuration? "
    $reset_config = $LastExitCode

    if ($reset_config -ne $Yes)
    {
        Choice /c yn /m "Configure TTS KeyMap on Next Startup? "
        $config_keymap = $LastExitCode
        Choice /c yn /m "Run Config Gui on Next Startup? "
        $run_config_gui = $LastExitCode
        Choice /c yn /m "Voice Introduction on next Config? "
        $voice_introduction = $LastExitCode
        Choice /c yn /m "Enable Hints in Config Gui? "
        $enable_hint = $LastExitCode
        Choice /c yn /m "Enable Help in Config Gui? "
        $enable_help = $LastExitCode
        Choice /c yn /m "Enable Extended Help in Config Gui? "
        $enable_extended_help = $LastExitCode
    }
    $config_file = $Global:TTS_Config_File
    $nl = ([Environment]::NewLine)

    Write-Log "config_file: $config_file"
    $tts_addon_dir = Split-Path -Path $config_file -Parent
    New-Item -Force -Path "$tts_addon_dir" -ItemType Directory

    $config_text = "reset_config $reset_config$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Force

    $config_text = "config_keymap $config_keymap$nl"
    Out-File -InputObject config_text -FilePath $config_file -Encoding utf8 -Append

    $config_text = "run_config_gui $run_config_gui$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Append

    $config_text = "enable_hint $enable_hint_text\$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Append

    $config_text = "enable_help $enable_help_text$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Append

    $config_text = "enable_extended_help $enable_extended_help$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Append

    $config_text = "voice_introduction $voice_introduction$nl"
    Out-File -InputObject $config_text -FilePath $config_file -Encoding utf8 -Append

    Trace_Entry_Exit "Exiting Configure_TTS"
}

function Pass_Parameters
{
    Param ([hashtable]$NamedParameters)
    return ($NamedParameters.GetEnumerator()|%{ "-$( $_.Key ) `"$( $_.Value )`"" }) -join " "
}

function Write-Log
{
    Param ([string] $message = "", [bool] $pause = $False)

    If ($Global:Trace_Debug)
    {
        Write-Debug -Message "$message"
        # Write-Host Host "output: $message"
        if ($pause)
        {
            $ignore = Read-Host -Prompt 'Press Enter to continue'
        }
    }
}

Function Trace_Entry_Exit
{
    Param ([string] $message = "", [bool] $pause = $False)
    If ($Global:Trace_Entry_Exit)
    {
        Write-Log "$message" $pause
    }
}
<#
    M A I N

    Set Admin privilege and install
#>

$Global:Startup_Delay = 5.0  # seconds
$Global:Stop_Delay = 1.5  # seconds
$Global:Enable_Delay = 1.0 # seconds
$Global:Restart_On_Addon_Change = $True
$Global:tmp_dir = "__kodiSRInstallerScript__"
$Global:workingDir = Join-Path "$env:tmp" "$Global:tmp_dir"
Write-Log "tmp: $env:tmp tmp_dir: $Global:tmp_dir working_dir:$Global:workingDir"
$Global:System_Drive = "$env:SystemDrive"
$Global:Kodi_url = "https://mirrors.kodi.tv/releases/windows/win64/kodi-21.2-Omega-x64.exe?https = 1"
# It is disgusting that spaces in file paths cause so much trouble on Windows.
# $Global:PROGRAM_FILES_SHORT = (New-Object -com scripting.filesystemobject).getFolder($env:PROGRAMFILES).ShortPath
$Global:PROGRAM_FILES = (New-Object -com scripting.filesystemobject).getFolder($env:PROGRAMFILES).Path
$Global:3rd_party_path = "$Global:PROGRAM_FILES"
$Global:Kodi_data_path = Join-Path "$env:APPDATA" "Kodi"
$Global:Kodi_gui_settings_path = Join-Path "$Global:Kodi_data_path" "userdata/gui_settings.xml"
$Global:Kodi_Program_Default_Path = Join-Path "$Global:PROGRAM_FILES" "Kodi"
$Global:Kodi_Program_Path = "$Global:Kodi_Program_Default_Path"
$Global:Install_Kodi = $False
$Global:Install_Repo = $False
$Global:Kodi_Install_Path = $null
$Global:Kodi_Install_Version = $null
$Global:Install_TTS = $False
$Global:TTS_Remove_Settings = $True
$Global:TTS_Remove_Cache = $True
$Global:TTS_Reset_Keymap = $True

$Global:Install_MPV = $False
# MPV download sites
# Site URL: "https: //github.com/zhongfly/mpv-winbuild/releases"
# $mpv_url = https://github.com/zhongfly/mpv-winbuild/releases/download/2025-12-07-dbd7a90/mpv-x86_64-20251207-git-dbd7a90.7z
# Download my copy (to keep path stable)
$mpv_file = "mpv-x86_64-20251207-git-dbd7a90.zip"
$Global:mpv_url = "https://feuerbacher.us/repo/3rd_party/$mpv_file"
$Global:mpv_zip_target = Join-Path "$Global:workingDir" "mpv.zip"
$Global:mpv_tmp_install = Join-Path "$Global:WorkingDir" "mpv"
$Global:mpv_install_path = Join-Path "$Global:PROGRAM_FILES" "mpv"

# An addon, such as service.kodi.tts, is packed in a zip that includes its version number (service.kodi.tts-2.3~alpha8.zip).
# The directory to install (copy to Kodi's addon directory) is at the top level in the zip and DOES NOT have a
# version number. So for this example, we copy service.kodi.tts from the unzipped folder named service.kodi.tts-2.3~alpha8.

# The ID is the addon-id
$Global:TTS_REPO_ID = "repo.fbacher"
$Global:TTS_SERVICE_ID = "service.kodi.tts"
$Global:SCRIPT_MODULE_LANGCODES_ID = "script.module.langcodes"
$Global:SCRIPT_MODULE_CHARDET_ID = "script.module.chardet"
$Global:SCRIPT_MODULE_SIX_ID = "script.module.six"
$Global:SCRIPT_MODULE_CERTIFI_ID = "script.module.certifi"
$Global:SCRIPT_MODULE_IDNA_ID = "script.module.idna"
$Global:SCRIPT_MODULE_REQUESTS_ID = "script.module.requests"
$Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID = "script.module.typing_extensions"
$Global:SCRIPT_MODULE_URLLIB3_ID = "script.module.urllib3"

$Global:OMEGA_URL = "https://mirrors.kodi.tv/addons/omega/"
$SCRIPT_MODULE_CHARDET_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_CHARDET_ID}/script.module.chardet-5.1.0.zip"
$SCRIPT_MODULE_SIX_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_SIX_ID}/script.module.six-1.16.0+matrix.1.zip"
$Global:SCRIPT_MODULE_IDNA_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_IDNA_ID}/script.module.idna-3.10.0.zip"
$SCRIPT_MODULE_REQUESTS_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_REQUESTS_ID}/script.module.requests-2.31.0.zip"
$SCRIPT_MODULE_TYPING_EXTENSIONS_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID}/script.module.typing_extensions-4.7.1.zip"
$SCRIPT_MODULE_URLLIB3_URL = "${Global:OMEGA_URL}/${Global:SCRIPT_MODULE_URLLIB3_ID}/script.module.urllib3-2.2.3.zip"

$Global:tts_repo_url = [string]"https://feuerbacher.us/repo/repo/zips/repo.fbacher/repo.fbacher-1.0.0.zip"
# Have to download directly from repository since json-rpc does not provide means to install from a repository.
# Update from repository should work.
$Global:tts_service_url = [String]"https://feuerbacher.us/repo/repo/zips/service.kodi.tts/service.kodi.tts-2.0.3~alpha8.zip"
$Global:tts_service_download = (Join-Path "$Global:workingDir" "tts_service.zip")
$Global:tts_service_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "service.kodi.tts"
$Global:tts_service_unzip = Join-Path "$Global:WorkingDir" "service.kodi.tts.unzip"
$Global:tts_repo_download = (Join-Path "$Global:workingDir" "repo.fbacher.zip")
$Global:tts_repo_unzip = Join-Path "$Global:workingDir" "repo.fbacher.unzip"
$Global:fbacher_repo_path = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "repo.fbacher"

$Global:script_module_chardet_url = "$SCRIPT_MODULE_CHARDET_URL"
$Global:script_module_chardet_download = (Join-Path "$Global:workingDir" "script.module.chardet.zip")
$Global:script_module_chardet_unzip = Join-Path "$Global:WorkingDir" "script.module.chardet.unzip"
$Global:script_module_chardet_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.chardet"

$Global:script_module_idna_url = "$SCRIPT_MODULE_IDNA_URL"
$Global:script_module_idna_download = (Join-Path "$Global:workingDir" "script.module.idna.zip")
$Global:script_module_idna_unzip = Join-Path "$Global:WorkingDir" "script.module.idna.unzip"
$Global:script_module_idna_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.idna"

$Global:script_module_certifi_url = "https://mirrors.kodi.tv/addons/omega/script.module.certifi/script.module.certifi-2023.5.7.zip"
$Global:script_module_certifi_download = (Join-Path "$Global:workingDir" "script.module.certifi.zip")
$Global:script_module_certifi_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.certifi"
$Global:script_module_certifi_unzip = Join-Path "$Global:WorkingDir" "script.module.certifi.unzip"

$Global:script_module_langcodes_url = [string]"https://feuerbacher.us/repo/repo/zips/script.module.langcodes/script.module.langcodes-3.4.0~alpha.zip"
$Global:script_module_langcodes_download = (Join-Path "$Global:workingDir" "script.module.langcodes.zip")
$Global:script_module_langcodes_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.langcodes"
$Global:script_module_langcodes_unzip = Join-Path "$Global:WorkingDir" "script.module.langcodes.unzip"

$Global:script_module_six_url = "$SCRIPT_MODULE_SIX_URL"
$Global:script_module_six_download = (Join-Path "$Global:workingDir" "script.module.six.zip")
$Global:script_module_six_unzip = Join-Path "$Global:WorkingDir" "script.module.six.unzip"
$Global:script_module_six_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.six"

$Global:script_module_requests_url = "$SCRIPT_MODULE_REQUESTS_URL"
$Global:script_module_requests_download = (Join-Path "$Global:workingDir" "script.module.requests.zip")
$Global:script_module_requests_unzip = Join-Path "$Global:WorkingDir" "script.module.requests.unzip"
$Global:script_module_requests_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.requests"

$Global:script_module_typing_extensions_url = "$SCRIPT_MODULE_TYPING_EXTENSIONS_URL"
$Global:script_module_typing_extensions_download = (Join-Path "$Global:workingDir" "script.module.typing_extensions.zip")
$Global:script_module_typing_extensions_unzip = Join-Path "$Global:WorkingDir" "script.module.typing_extensions.unzip"
$Global:script_module_typing_extensions_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.typing_extensions"

$Global:script_module_urllib3_url = "$SCRIPT_MODULE_URLLIB3_URL"
$Global:script_module_urllib3_download = (Join-Path "$Global:workingDir" "script.module.urllib3.zip")
$Global:script_module_urllib3_unzip = Join-Path "$Global:WorkingDir" "script.module.urllib3.unzip"
$Global:script_module_urllib3_install = Join-Path (Join-Path "$Global:Kodi_data_path" "addons") "script.module.urllib3"

$Global:download_sources = [ordered]@{
    $Global:TTS_REPO_ID = "$Global:tts_repo_url"
    $Global:SCRIPT_MODULE_SIX_ID = "$SCRIPT_MODULE_SIX_URL"
    $Global:SCRIPT_MODULE_CHARDET_ID = "$SCRIPT_MODULE_CHARDET_URL"
    $Global:SCRIPT_MODULE_IDNA_ID = "$SCRIPT_MODULE_IDNA_URL"
    $Global:SCRIPT_MODULE_URLLIB3_ID = "$SCRIPT_MODULE_URLLIB3_URL"
    $Global:SCRIPT_MODULE_CERTIFI_ID = "$script_module_certifi_url"
    $Global:SCRIPT_MODULE_REQUESTS_ID = "$SCRIPT_MODULE_REQUESTS_URL"
    $Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID = "$SCRIPT_MODULE_TYPING_EXTENSIONS_URL"
    $Global:SCRIPT_MODULE_LANGCODES_ID = "$Global:script_module_langcodes_url"
    $Global:TTS_SERVICE_ID = "$Global:tts_service_url"
}

# These .zip files are unpacked in a tmp directory, with the .unzip suffix.
$Global:download_destination = @{
    $Global:TTS_REPO_ID = $Global:tts_repo_download
    $Global:TTS_SERVICE_ID = $Global:tts_service_download
    $Global:SCRIPT_MODULE_LANGCODES_ID = $Global:script_module_langcodes_download
    $Global:SCRIPT_MODULE_CHARDET_ID = "$Global:script_module_chardet_download"
    $Global:SCRIPT_MODULE_IDNA_ID = "$Global:script_module_idna_download"
    $Global:SCRIPT_MODULE_SIX_ID = "$script_module_six_download"
    $Global:SCRIPT_MODULE_URLLIB3_ID = "$script_module_urllib3_download"
    $Global:SCRIPT_MODULE_CERTIFI_ID = "$script_module_certifi_download"
    $Global:SCRIPT_MODULE_REQUESTS_ID = "$script_module_requests_download"
    $Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID = "$script_module_typing_extensions_download"
}

# There should be a single top-level directory with the same name as the addon-id.
# This top-level directory is what is copied to kodi's addon directory.
$Global:download_unzip = @{
    $Global:TTS_REPO_ID = "$Global:tts_repo_unzip"
    $Global:TTS_SERVICE_ID = "$Global:tts_service_unzip"
    $Global:SCRIPT_MODULE_LANGCODES_ID = "$Global:script_module_langcodes_unzip"
    $Global:SCRIPT_MODULE_SIX_ID = "$Global:script_module_six_unzip"
    $Global:SCRIPT_MODULE_IDNA_ID = "$Global:script_module_idna_unzip"
    $Global:SCRIPT_MODULE_CHARDET_ID = "$Global:script_module_chardet_unzip"
    $Global:SCRIPT_MODULE_URLLIB3_ID = "$Global:script_module_urllib3_unzip"
    $Global:SCRIPT_MODULE_CERTIFI_ID = "$script_module_certifi_unzip"
    $Global:SCRIPT_MODULE_REQUESTS_ID = "$Global:script_module_requests_unzip"
    $Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID = "$Global:script_module_typing_extensions_unzip"
}

# Placing the addon source into the kodi/addons directory completes the 'installation'
$Global:install_destination = @{
    $Global:TTS_REPO_ID = "$Global:fbacher_repo_path"
    $Global:TTS_SERVICE_ID = "$Global:tts_service_install"
    $Global:SCRIPT_MODULE_LANGCODES_ID = "$Global:script_module_langcodes_install"
    $Global:SCRIPT_MODULE_SIX_ID = "$Global:script_module_six_install"
    $Global:SCRIPT_MODULE_IDNA_ID = "$Global:script_module_idna_install"
    $Global:SCRIPT_MODULE_CHARDET_ID = "$Global:script_module_chardet_install"
    $Global:SCRIPT_MODULE_URLLIB3_ID = "$Global:script_module_urllib3_install"
    $Global:SCRIPT_MODULE_CERTIFI_ID = "$script_module_certifi_install"
    $Global:SCRIPT_MODULE_REQUESTS_ID = "$Global:script_module_requests_install"
    $Global:SCRIPT_MODULE_TYPING_EXTENSIONS_ID = "$Global:script_module_typing_extensions_install"
}

$Global:WindowStyle_Normal = 0
$Global:WindowStyle_Hidden = 1
$Global_WindowStyle_Minimum = 2
$Global_WindowStyle_Maximum = 3

# Record whether the addon is already installed. (Yeah, overkill, but easy to Grok).
# The ones that are missing will be changed to $True
$Global:installed_state = [ordered]@{ }
foreach ($key in $Global:download_sources.keys)
{
    $Global:installed_state[$key] = $False
}

$Global:TTS_Config_File = Join-Path "$Global:Kodi_data_path" "userdata/addon_data/service.kodi.tts/config"

Prepare_Working_Dir -create_working_dir $True -delete_working_dir $True

Get_Kodi_Location
Review_TTS_Settings

# Get external programs like mpv, which TTS may depend upon. Best to have them ready before needed.

Get_Optional_Images
Install_3rd_Party_Images
if ($Global:Install_Kodi)
{
    Install_Kodi
}
Get_Addon_Images
Install_Images

# Garbage Collect
# Prepare_Working_Dir -create_working_dir $True -delete_working_dir $True

Write-Log "FINITE"
$response = Read-Host -Prompt "Script Finished"
Write-Log "response: $response"
Start_Kodi -Window_Style $Global:WindowStyle_Normal -Sleep 0
