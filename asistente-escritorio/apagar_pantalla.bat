@echo off
REM Apaga solo la pantalla (monitor), el PC sigue encendido
REM No pide contraseña, no suspende, no hiberna
powershell -command "Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class ScreenOff{[DllImport(\"user32.dll\")]public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);}'; [ScreenOff]::SendMessage(-1,0x0112,0xF170,2)"