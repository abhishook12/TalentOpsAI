Set WshShell = CreateObject("WScript.Shell")
Set objArgs = Wscript.Arguments
argStr = ""
If objArgs.Count > 0 Then
    argStr = " " & objArgs(0)
End If
WshShell.Run Chr(34) & "C:\Python314\pythonw.exe" & Chr(34) & " " & Chr(34) & "c:\TalentOpsAI\autostart_talentops.py" & Chr(34) & argStr, 0, False
Set WshShell = Nothing
