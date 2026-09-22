@echo off
chcp 65001 >nul

set BOT_PROCESS=pythonw.exe
set BOT_SCRIPT=bot.py

:: Проверка запущенного бота
wmic process where "name='%BOT_PROCESS%'" get commandline | find /i "%BOT_SCRIPT%" > nul

if %errorlevel% == 0 (
    :: Если бот запущен - останавливаем все соответствующие процессы
    wmic process where "name='%BOT_PROCESS%' and commandline like '%%%BOT_SCRIPT%%%'" delete > nul
    powershell -command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('Бот успешно остановлен', 'Уведомление', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
) else (
    :: Если бот не запущен - запускаем
    start "" %BOT_PROCESS% %BOT_SCRIPT%
    powershell -command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('Бот успешно запущен', 'Уведомление', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
)