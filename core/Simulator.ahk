#Include <ImageFinder>
#Include <Settings>

class Simulator {

    __New() {
        ; Metadata
        this.CHAMPION := ""
        this.SCREEN_CENTER := [A_ScreenWidth / 2, (A_ScreenHeight / 2) - 10]
        this.CLIENT_PROCESS := "ahk_exe LeagueClientUx.exe"
        this.GAME_PROCESS := "ahk_exe League of Legends.exe"
        this.CLIENT_CLASSNN := "Chrome_RenderWidgetHostHWND1"
        
        ; Controls
        this.CENTER_CAMERA := ""
        this.HOLD_TO_LEVEL := ""
        this.ITEM_1 := ""
        this.ITEM_2 := ""
        this.ITEM_3 := ""
        this.ITEM_4 := ""
        this.ITEM_5 := ""
        this.ITEM_6 := ""
        this.RECALL := ""
        this.SELECT_ALLY_1 := ""
        this.SELECT_ALLY_2 := ""
        this.SELECT_ALLY_3 := ""
        this.SELECT_ALLY_4 := ""
        this.SHOP := ""
        this.SPELL_1 := ""
        this.SPELL_2 := ""
        this.SPELL_3 := ""
        this.SPELL_4 := ""
        this.SUM_1 := ""
        this.SUM_2 := ""
    
        ; Load config file
        infile := FileOpen(A_ScriptDir "\config.cfg", "r")
        if (!infile) {
            MsgBox("Error reading config file.")
            return
        }
        configFileContent := infile.read()
        infile.Close()
    
        ; Parsing config file
        lines := StrSplit(configFileContent, "`n", "`r")
        for index, line in lines {
            keyValue := StrSplit(line, "=")
            if (keyValue.Length >= 2) {
                Switch keyValue[1] {
                    case "Center camera":
                        this.CENTER_CAMERA := keyValue[2]
                    case "Champion name":
                        this.CHAMPION := keyValue[2]
                    case "Hold to Level":
                        this.HOLD_TO_LEVEL := keyValue[2]
                    case "Item 1":
                        this.ITEM_1 := keyValue[2]
                    case "Item 2":
                        this.ITEM_2 := keyValue[2]
                    case "Item 3":
                        this.ITEM_3 := keyValue[2]
                    case "Item 4":
                        this.ITEM_4 := keyValue[2]
                    case "Item 5":
                        this.ITEM_5 := keyValue[2]
                    case "Item 6":
                        this.ITEM_6 := keyValue[2]
                    case "Recall":
                        this.RECALL := keyValue[2]
                    case "Select Ally 1":
                        this.SELECT_ALLY_1 := keyValue[2]
                    case "Select Ally 2":
                        this.SELECT_ALLY_2 := keyValue[2]
                    case "Select Ally 3":
                        this.SELECT_ALLY_3 := keyValue[2]
                    case "Select Ally 4":
                        this.SELECT_ALLY_4 := keyValue[2]
                    case "Shop":
                        this.SHOP := keyValue[2]
                    case "Spell 1":
                        this.SPELL_1 := keyValue[2]
                    case "Spell 2":
                        this.SPELL_2 := keyValue[2]
                    case "Spell 3":
                        this.SPELL_3 := keyValue[2]
                    case "Spell 4":
                        this.SPELL_4 := keyValue[2]
                    case "Sum 1":
                        this.SUM_1 := keyValue[2]
                    case "Sum 2":
                        this.SUM_2 := keyValue[2]
                }
            }
        }

        ; Post config properties
        this.ImageFinder := ImageFinder()
        this.MAX_ORDER := [this.SPELL_4,this.SPELL_1,this.SPELL_2,this.SPELL_3]
        this.CAST_ORDER := [this.SPELL_4,this.SPELL_1,this.SPELL_2,this.SPELL_3]
    }    

/*
-------------------------------
            Client
-------------------------------
*/

;Accepts queue and picks champ
RunClient(champName := "") {
    if this.ImageFinder.IsPickingChamp() {
        while (this.ImageFinder.IsPickingChamp() == True) {
            this.ClientClick(60, 14) ;search bar
            Sleep(500)
            this.ClientClick(30, 22) ;random champ icon
            Sleep(500)
            this.ClientClick(60, 14) ;search bar
            Send(champName)
            Sleep(500)
            this.ClientClick(30, 22) ;user champ icon
            Sleep(500)
            this.ClientClick(50, 85) ;lock in
            Sleep(500)
        }
    } else {
        this.ClientClick(46, 95) ;find match
        this.ClientClick(50, 78) ;accept queue
        Sleep(1000)
        this.ImageFinder.CloseFeedback()
    }
}

;Move mouse % window distance
ClientClick(xPercent, yPercent) {
    if (WinActive(this.CLIENT_PROCESS)) {
        WinGetPos(&X, &Y, &W, &H, this.CLIENT_PROCESS)
        xFlat := W*1/100*xPercent
        yFlat := H*1/100*yPercent
        MouseMove xFlat, yFlat
        ControlClick(this.CLIENT_CLASSNN, this.CLIENT_PROCESS,,,,"x" xFlat "y" yFlat)
        Sleep 100
    }
}

;Gets cursor pos by reference
GetCursorPos(&x, &y) {
    point := Buffer(8)
    if DllCall("GetCursorPos", "Ptr", point) {
        x := NumGet(point, 0, "Int")
        y := NumGet(point, 4, "Int")
        return true
    }
    return false
}

;Move mouse by a percentage of the screen distance from the current position
MoveCursorRelative(xPercent, yPercent) {
    xMove := A_ScreenWidth * (xPercent / 100)
    yMove := A_ScreenHeight * (yPercent / 100)
    if this.GetCursorPos(&currentX, &currentY) {
        newX := currentX + xMove
        newY := currentY + yMove
        DllCall("SetCursorPos", "Int", Round(newX), "Int", Round(newY))
    } else {
        MsgBox("Failed to get the current cursor position")
    }
}

;Move mouse randomly some offset away from (x,y)
MoveCursorRandom(x, y, offset) {
    RandX := Random(x - offset, x + offset)
    RandY := Random(y - offset, y + offset)
    DllCall("SetCursorPos", "int", RandX, "int", RandY)
}

GetDistance(point1, point2) {
    return Sqrt((point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)
}

;Level all four abilities
LevelUp() {
    Send("{" this.HOLD_TO_LEVEL " down}")
    if(!this.MAX_ORDER) {
        Send(this.SPELL_4)
        Send(this.SPELL_1)
        Send(this.SPELL_2)
        Send(this.SPELL_3)
    } else {
        Send(this.MAX_ORDER[1])
        Send(this.MAX_ORDER[2])
        Send(this.MAX_ORDER[3])
        Send(this.MAX_ORDER[4])
    }
    Send("{" this.HOLD_TO_LEVEL " up}")
}

;Level the given ability
LevelUpSingle(spell) {
    Send("{" this.HOLD_TO_LEVEL " down}")
    Send(spell)
    Send("{" this.HOLD_TO_LEVEL " up}")
    Sleep(500)
}

;Buy all of a given list of items
BuyList(ITEM_LIST) {
    Send("{" this.SHOP "}")
    Sleep(500)
    Loop ITEM_LIST.Length {
        Send("^l")
        Sleep(200)
        Send(ITEM_LIST[A_Index])
        Sleep(500)
        Send("{Enter}")
        Sleep(200)
    }
    Send("{" this.SHOP "}")
    Sleep(500)
}

;Buy the middle recommended item, offset to the right
BuyRecommended() {
    Send("{" this.SHOP "}")
    Sleep(500)
    if(ShopFlag := this.ImageFinder.ShopOpen()) {
        DllCall("SetCursorPos", "int", ShopFlag[1], "int", ShopFlag[2])
        Sleep(500)
        this.MoveCursorRelative(0, -62)
        Click("left")
        Sleep(500)
        DllCall("SetCursorPos", "int", ShopFlag[1], "int", ShopFlag[2])
        this.MoveCursorRelative(17, -20)
        Loop 5 {
            Click("Right down")
            Sleep(200)
            Click("Right up")
        }
    }
    Sleep(500)
    Send("{" this.SHOP "}")
}

;Buy legendary anvil in Arena
BuyLegendaryAnvil() {
    if(ShopFlag := this.ImageFinder.ShopOpen()) {
        DllCall("SetCursorPos", "int", ShopFlag[1], "int", ShopFlag[2])
        Sleep(500)
        this.MoveCursorRelative(14, -62)
        Click
        Sleep(500)
        DllCall("SetCursorPos", "int", ShopFlag[1], "int", ShopFlag[2])
        this.MoveCursorRelative(5, -25)
        Click("Right down")
        Sleep(200)
        Click("Right up")
        Sleep(500)
        Send("{" this.SHOP "}")
        Sleep(500)
        DllCall("SetCursorPos", "int", this.SCREEN_CENTER[1], "int", this.SCREEN_CENTER[2])
        Click
        Sleep 400
    }
}

;Follow ally based on SelectAlly key
FollowAlly(ally_key, offset) {
    Send("{" ally_key " down}")
    this.MoveCursorRandom(this.SCREEN_CENTER[1], this.SCREEN_CENTER[2], offset)
    Click("Right")
    Send("{" ally_key " up}")
}

;Attack enemy with specified cast order
AttackEnemy(&EnemyPosXY) {
    Click("Right")
    Loop this.CAST_ORDER.Length {
        DllCall("SetCursorPos", "int", EnemyPosXY[1], "int", EnemyPosXY[2])
        ability := this.CAST_ORDER[A_Index]
        Send(ability)
    }
    Send("{" this.ITEM_1 "}")
    Send("{" this.ITEM_2 "}")
    Send("{" this.ITEM_3 "}")
    Send("{" this.ITEM_4 "}")
    Send("{" this.ITEM_5 "}")
    Send("{" this.ITEM_6 "}")
}

;Moves in opposite direction of enemy
Retreat(duration) {
    Send("{" this.CENTER_CAMERA " down}")
    EnemyPosXY := this.ImageFinder.FindEnemyXY()
    awayX := this.SCREEN_CENTER[1] + ((this.SCREEN_CENTER[1] - EnemyPosXY[1]) << 3)
    awayY := this.SCREEN_CENTER[2] + ((this.SCREEN_CENTER[2] - EnemyPosXY[2]) << 3)
    DllCall("SetCursorPos", "int", awayX, "int", awayY)
    Click("down, Right")
    Sleep(duration)
    Click("up, Right")
    Send("{" this.CENTER_CAMERA " up}")
}

;Attempts recall. breaks if enemy OR ally is present
AttemptRecall() {
    if (this.ImageFinder.FindEnemyXY() || this.ImageFinder.FindAllyXY()) {
        return false
    }
    Send("{" this.RECALL "}")
    startTime := A_TickCount
    while (!this.ImageFinder.FindEnemyXY() && !this.ImageFinder.FindAllyXY()) {
        if (A_TickCount - startTime > 9000) {
            this.BuyRecommended()
            this.LevelUp()
            return true
        }
    }
    return false
}

;Types in surrender vote /ff
Surrender() {
    Send("{Enter}")
    Sleep 200
    Send("/ff")
    Send("{Enter}")
}

/*
-------------------------------
  Testing and Utility
-------------------------------
*/

; tests speed of a run
TimeTest() {
    NumRuns := 30
    TotalRuntime := 0
    loop NumRuns {
        StartTime := A_TickCount
        ;RUN FUNCTION HERE
        /*****************/

        /*****************/
        TotalRuntime := TotalRuntime + (A_TickCount - StartTime)
    }
    MsgBox "Total Time: " TotalRuntime " ms"
        .  "`n`nAverage Time: " TotalRuntime / NumRuns " ms"
}

; Checks image found + info
ImageFound(searchResult) {
    t1 := A_TickCount
    MsgBox "Found:`t" (IsObject(searchResult)?searchResult.Length:searchResult)
      . "`n`nTime:`t" (A_TickCount - t1) " ms"
      . "`n`nResult:`t<" (IsObject(searchResult)?searchResult[1].id:"") ">", "Tip", 4096
}

; Prints all keys
PrintKeys() {
    ; Concat keys to string
    pressedKeys .= "Center Camera: " this.CENTER_CAMERA . "`n"
    pressedKeys .= "Hold to Level: " this.HOLD_TO_LEVEL . "`n"
    pressedKeys .= "Recall: " this.RECALL . "`n"
    pressedKeys .= "Shop: " this.SHOP . "`n"
    pressedKeys .= "Spell 1: " this.SPELL_1 . "`n"
    pressedKeys .= "Spell 2: " this.SPELL_2 . "`n"
    pressedKeys .= "Spell 3: " this.SPELL_3 . "`n"
    pressedKeys .= "Spell 4: " this.SPELL_4 . "`n"
    pressedKeys .= "Sum 1: " this.SUM_1 . "`n"
    pressedKeys .= "Sum 2: " this.SUM_2 . "`n"
    pressedKeys .= "Item 1: " this.ITEM_1 . "`n"
    pressedKeys .= "Item 2: " this.ITEM_2 . "`n"
    pressedKeys .= "Item 3: " this.ITEM_3 . "`n"
    pressedKeys .= "Item 4: " this.ITEM_4 . "`n"
    pressedKeys .= "Item 5: " this.ITEM_5 . "`n"
    pressedKeys .= "Item 6: " this.ITEM_6 . "`n"
    pressedKeys .= "Select Ally 1: " this.SELECT_ALLY_1 . "`n"
    pressedKeys .= "Select Ally 2: " this.SELECT_ALLY_2 . "`n"
    pressedKeys .= "Select Ally 3: " this.SELECT_ALLY_3 . "`n"
    pressedKeys .= "Select Ally 4: " this.SELECT_ALLY_4 . "`n"

    ; Display the pressed keys in a message box
    MsgBox pressedKeys
}

; Prints config file content
PrintConfig() {
    infile := FileOpen(A_ScriptDir "\config.cfg", "r")
    if (!infile) {
        MsgBox("Error reading config file.")
        return
    }
    configFileContent := infile.read()
    infile.Close()

    MsgBox(configFileContent)
}

; Prints metadata
PrintMetaData() {
    constants .= "Client Process: " . this.CLIENT_PROCESS . "`n"
    constants .= "Game Process: " . this.GAME_PROCESS . "`n"
    constants .= "Screen Center: " . this.SCREEN_CENTER[1] . ", " . this.SCREEN_CENTER[2] . "`n"
    MsgBox(constants)
}

; Prints a_script dir
PrintADir(){
    currentDir := A_ScriptDir
    fileList := ""
    Loop Files, currentDir "\*.*", "FD"
    {
        fileList .= A_LoopFileName "`n" 
    }
    MsgBox "Files in " currentDir ":`n`n" fileList
}

} ; End class