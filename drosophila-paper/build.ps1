# DrosophilaBee Local Build Script
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

$jdkPath = ""
$candidates = @(
    "C:\Program Files\Java\jdk-25.0.2\bin",
    "C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin",
    "C:\Program Files\Eclipse Adoptium\jdk-17.0.14.7-hotspot\bin"
)
foreach ($c in $candidates) {
    if (Test-Path "$c\javac.exe") {
        $jdkPath = $c
        break
    }
}
if (-not $jdkPath) {
    $found = Get-ChildItem "C:\Program Files\Eclipse Adoptium", "C:\Program Files\Java" -Filter "javac.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $jdkPath = $found.DirectoryName
    }
}

if (-not $jdkPath -or -not (Test-Path "$jdkPath\javac.exe")) {
    Write-Error "JDK bulunamadı! Lütfen JDK kurulu olduğundan emin olun."
    exit 1
}

Write-Host "Kullanılan JDK: $jdkPath" -ForegroundColor Cyan

$buildDir = "build\classes"
$targetDir = "target"
$spigotJar = "lib\spigot-api.jar"
$wsJar = "lib\Java-WebSocket-1.5.7.jar"

if (-not (Test-Path $wsJar)) {
    Write-Host "Java-WebSocket kütüphanesi indiriliyor..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://repo1.maven.org/maven2/org/java-websocket/Java-WebSocket/1.5.7/Java-WebSocket-1.5.7.jar" -OutFile $wsJar
}

$classpath = "$spigotJar;$wsJar"

if (Test-Path $buildDir) { Remove-Item -Recurse -Force "$buildDir\*" -ErrorAction SilentlyContinue }
if (Test-Path $targetDir) { Remove-Item -Recurse -Force "$targetDir\*" -ErrorAction SilentlyContinue }

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$javaFiles = Get-ChildItem -Recurse -Path "src\main\java" -Filter "*.java" | ForEach-Object { $_.FullName }
Write-Host "Derlenen Java dosyaları: $($javaFiles.Count) adet" -ForegroundColor Green

# JDK sürümüne göre release bayrağı
$releaseVer = "17"
$verOut = & "$jdkPath\javac.exe" -version 2>&1
if ($verOut -match "javac\s+(2[1-9])") {
    $releaseVer = "21"
}

Write-Host "Hedef Java Sürümü: --release $releaseVer" -ForegroundColor Cyan
& "$jdkPath\javac.exe" -encoding UTF-8 -cp "$classpath" -d "$buildDir" --release $releaseVer $javaFiles

if ($LASTEXITCODE -ne 0) {
    Write-Error "Java derleme hatası!"
    exit 1
}

# Kaynak dosyalarını kopyala (plugin.yml, config.yml)
Copy-Item -Path "src\main\resources\*" -Destination "$buildDir" -Recurse -Force

# Java-WebSocket kütüphanesini build klasörüne aç (Fat/Shaded JAR için)
Write-Host "Java-WebSocket sınıfları ekleniyor..." -ForegroundColor Cyan
Push-Location "$buildDir"
& "$jdkPath\jar.exe" -xf "..\..\$wsJar"
Remove-Item -Recurse -Force "META-INF\maven*" -ErrorAction SilentlyContinue
Remove-Item -Force "META-INF\MANIFEST.MF" -ErrorAction SilentlyContinue
Pop-Location

# JAR paketle
$jarPath = "$targetDir\DrosophilaBee.jar"
& "$jdkPath\jar.exe" --create --file "$jarPath" -C "$buildDir" .

if ($LASTEXITCODE -ne 0) {
    Write-Error "JAR paketleme hatası!"
    exit 1
}

Write-Host "=========================================" -ForegroundColor Green
Write-Host "BAŞARILI: $jarPath oluşturuldu!" -ForegroundColor Green
$item = Get-Item $jarPath
Write-Host "Boyut: $([math]::Round($item.Length / 1024, 2)) KB" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Pop-Location
