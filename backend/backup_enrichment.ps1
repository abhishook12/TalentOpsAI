$runId = 'full-enrichment-20260624-023600'
$line = (Select-String -Path 'C:\\TalentOpsAI\\backend\\.env' -Pattern '^DATABASE_URL=').Line
$url = $line -replace '^DATABASE_URL=', ''
# Strip scheme
$url = $url -replace '^postgresql\+psycopg://', ''
$parts = $url -split '@'
$auth = $parts[0]
$hostPortDb = $parts[1]
$u,$p = $auth -split ':'
$hostPort,$db = $hostPortDb -split '/',2
$hostName,$portNumber = $hostPort -split ':'
$env:PGPASSWORD = $p
$backupDir = "C:\\TalentOpsAI\\backups\\enrichment\\$runId"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
pg_dump -Fc -U $u -h $hostName -p $portNumber -d $db -f "${backupDir}\\dump.backup"
