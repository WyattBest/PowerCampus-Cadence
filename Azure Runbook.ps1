<# 
.SYNOPSIS 
    Executes an SQL stored procedure to update the SMS opt-in status for a student and department.
 
.DESCRIPTION 
    TODO
 
.PARAMETER SqlServer 
    String name of the SQL Server to connect to.
 
.PARAMETER SqlServerPort 
    Integer port to connect to the SQL Server. Default is 1433.
 
.PARAMETER Database 
    String name of the SQL Server database to connect to.
 
.PARAMETER SqlCredentialAsset 
    Credential asset name containing a username and password with access to the SQL Server.

.PARAMETER WebhookData
    Data passed in from a webhook call.
 
.NOTES 
    AUTHOR: Wyatt Best
    LASTEDIT: 2021-07-14
#>
param( 
    [parameter(Mandatory = $True)]
    [string] $SqlServer,
     
    [parameter(Mandatory = $False)]
    [int] $SqlServerPort = 1433, 
     
    [parameter(Mandatory = $True)]
    [string] $Database,
     
    [parameter(Mandatory = $True)]
    [string] $SqlCredentialAsset,

    [parameter(Mandatory = $False)]
    [object] $WebhookData
) 

$errorActionPreference = "Stop"
# Write-Output $WebhookData.RequestBody

# Read parameters from HTTP POST body
$PostData = (ConvertFrom-Json $WebhookData.RequestBody)
$studentId = $PostData.studentId
$departmentCode = $PostData.departmentCode
$optedIn = $PostData.optedIn

Write-Output "Preparing to set opt-in status for $studentId in department $departmentCode to $optedIn."

$SqlCredential = Get-AutomationPSCredential -Name $SqlCredentialAsset 
if ($null -eq $SqlCredential) { 
    throw "Could not retrieve '$SqlCredentialAsset' credential asset. Check that you created this first in the Automation service." 
}   
# Get the username and password from the SQL Credential 
$SqlUsername = $SqlCredential.UserName 
$SqlPass = $SqlCredential.GetNetworkCredential().Password 

# Open the SQL connection
$Conn = New-Object System.Data.SqlClient.SqlConnection("Server=tcp:$SqlServer,$SqlServerPort;Database=$Database;User ID=$SqlUsername;Password=$SqlPass;Trusted_Connection=False;Encrypt=True;Connection Timeout=30;")
$Conn.Open()

# Define the SQL command to run
$Cmd = new-object system.Data.SqlClient.SqlCommand("[custom].[CadenceUpdateSMSOpt] $studentId, $departmentCode, $optedIn, 'Cadence'", $Conn)
$Cmd.CommandTimeout = 30

# Execute the SQL command
$Ds = New-Object system.Data.DataSet
$Da = New-Object system.Data.SqlClient.SqlDataAdapter($Cmd)
[void]$Da.fill($Ds)
 
# Output the count
$Rowcount = $Ds.Tables.Column1
Write-Output "Done with rowcount: $Rowcount"

# Close the SQL connection 
$Conn.Close()
