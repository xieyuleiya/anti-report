Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 切换到脚本目录
WshShell.CurrentDirectory = ScriptDir

' 构建 Python 路径
Dim pythonExe
If fso.FileExists(ScriptDir & "\.venv\Scripts\pythonw.exe") Then
    ' 使用虚拟环境中的 pythonw.exe（无窗口模式）
    pythonExe = """" & ScriptDir & "\.venv\Scripts\pythonw.exe" & """"
ElseIf fso.FileExists(ScriptDir & "\.venv\Scripts\python.exe") Then
    ' 使用虚拟环境中的 python.exe
    pythonExe = """" & ScriptDir & "\.venv\Scripts\python.exe" & """"
Else
    ' 使用系统 Python（优先尝试 pythonw.exe，无窗口模式）
    If fso.FileExists("C:\Windows\py.exe") Then
        ' 使用 Python Launcher
        pythonExe = "pyw"
    Else
        ' 尝试使用 pythonw.exe
        On Error Resume Next
        Dim testExec
        Set testExec = WshShell.Exec("pythonw --version")
        testExec.StdOut.ReadAll
        testExec.Wait
        If testExec.ExitCode = 0 Then
            pythonExe = "pythonw"
        Else
            pythonExe = "python"
        End If
        On Error Goto 0
    End If
End If

' 运行 Python 程序
' 参数说明：第二个参数 0=隐藏窗口，1=显示窗口
WshShell.Run pythonExe & " """ & ScriptDir & "\unified_gui.py""", 0, False

Set WshShell = Nothing
Set fso = Nothing
