# TTS: "시작초|문장" 줄마다 <OutDir>\<줄번호>.wav 를 만든다. Windows 에 깔린 목소리(Microsoft Heami, ko-KR)를 쓴다 — 받는 것·인터넷 없음.
param([string]$Lines, [string]$OutDir, [int]$Rate = 0)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice("Microsoft Heami Desktop"); $s.Rate = $Rate
$i = 0
Get-Content $Lines -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object {
    $s.SetOutputToWaveFile((Join-Path $OutDir "$i.wav")); $s.Speak($_.Split('|', 2)[1]); $i++
}
$s.Dispose()
