﻿

#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.
#Include socket_nonblock.ahk				; Non block 2021/1/8
SetBatchLines -1



Gui, add, button, w80 h30 gbutton1, REUTER
Gui, add, button, xp+100 yp w80 h30 gbutton2 hwndhbutton2, APTN
Gui, add, button, xp+100 yp w80 h30 gbutton3 hwndhbutton3, CNN

Gui, add, button, xp+200 yp w80 h30 gbutton6 hwndhbutton6, FORCE ENCODE
Gui, add, button, xp+110 yp w80 h30 gbutton7 hwndhbutton7, SHUTDOWN
Gui, add, button, xp+110 yp w80 h30 gbutton8 hwndhbutton8, STATUS
Gui, add, button, xp+110 yp w80 h30 gbutton9 hwndhbutton9, FTP LIST

Gui, add, Edit, xm yp+35 w600 h30 -multi hwndheditbox veditbox, custom command <set_stt_on>
Gui, add, button, xp+610 yp w80 h30 gbutton30 hwndhbutton30, CUSTOM

Gui, add, ListView, xm  yp+40  w900 h420 hwndhlv1 NoSort NoSortHdr gclicklv1, NO|FILENAME|TS
Gui, add, ListView, xm  yp+430 w900 h200 hwndhlv2 NoSort NoSortHdr gclicklv2, NO|FILENAME|TS
;Gui, add, Edit, w900 h20 hwndhinput vtestinput, type here..
Gui, add, button, xm w80 h30 gbutton4 hwndhbutton4, SAVE`nMEDIA
Gui, add, button, xp+110 yp w80 h30 gbutton5 hwndhbutton5, SAVE`nSTORY

Gui, add, button, xp+110 yp w80 h30 gbutton20 hwndhbutton20, MEDIALIST
Gui, add, button, xp+110 yp w80 h30 gbutton21 hwndhbutton21, RAW`nSTORY
Gui, add, button, xp+110 yp w80 h30 gbutton22 hwndhbutton22, UPDATE`nSTORY
Gui, add, button, xp+110 yp w80 h30 gbutton23 hwndhbutton23, GET_JOBS
Gui, add, Edit, xm yp+35 w900 h300 hwndhtext Multi, message
Gui, add, StatusBar, hwndhstatus, Statusbar


Gui, show,, sendust news client

; reuter = port 4000
;udprecv := new class_udprecv("0.0.0.0", 4000)
;tcpsend := new class_tcpsend("10.10.108.203", 4001)


; aptn = port 7890
;udprecv := new class_udprecv("0.0.0.0", 7890)
;tcpsend := new class_tcpsend("10.10.108.203", 7891)

rdata := new large_text()
ftproot := Object()
ftproot := {"reuters" : "/reuters/", "aptn" : "/aptn/", "cnn" : "/cnn/" }
ftproot.choice := ftproot["reuters"]



lv1 := new c_lv(hlv1, 3)			; LV handle, column max
lv2 := new c_lv(hlv2, 3)


ftp := new wget()
;ftp.connect("202.31.153.221", 50080, "sbsint", "0000")
return


button30:

Gui, submit, nohide
tcpsend.sendtext(editbox)

return

button1:

udprecv := Object()
tcpsend := Object()
; reuter = port 50011
udprecv := new class_udprecv("0.0.0.0", 50012)
tcpsend := new class_tcpsend("202.31.153.221", 50011)
tcpsend.sendtext("<get_income>")
ftproot.choice := ftproot["reuters"]
updatestatus(ftproot.choice)
return


button2:

udprecv := Object()
tcpsend := Object()
; aptn = port 50021
udprecv := new class_udprecv("0.0.0.0", 50022)
tcpsend := new class_tcpsend("202.31.153.221", 50021)
tcpsend.sendtext("<get_income>")
ftproot.choice := ftproot["aptn"]
updatestatus(ftproot.choice)

return


button3:

udprecv := Object()
tcpsend := Object()
; cnn = port 50031
udprecv := new class_udprecv("0.0.0.0", 50032)
tcpsend := new class_tcpsend("202.31.153.221", 50031)
tcpsend.sendtext("<get_income>")
ftproot.choice := ftproot["cnn"]
updatestatus(ftproot.choice)

return


button4:
updatestatus("Start transfer..")
ftp.get_file(ftproot.choice . ftproot.file_selected)
updatestatus("Finish transfer..")
return


button5:
write_story(ftproot.file_selected, rdata.get_text())
return

button6:
tcpsend.sendtext("<do_encode><" . lv1.getselected_text() . ">")
return


button7:
tcpsend.sendtext("<do_shutdown>")
return


button8:
tcpsend.sendtext("<get_status>")
return


button9:
tcpsend.sendtext("<get_incomelist>")
return


button3333:
Gui, Submit, NoHide
tcpsend.sendtext("<get_scdata><" . testinput . ">")
return

button20:
tcpsend.sendtext("<get_media><" . lv2.getselected_text() . ">" )
return


button21:
tcpsend.sendtext("<get_rawscript><" . lv2.getselected_text() . ">" )
return


button22:
tcpsend.sendtext("<update_scdata><" . lv2.getselected_text() . ">" )
return


button23:
tcpsend.sendtext("<get_jobs>" )
return



test111:
Gui, Submit, NoHide
tcpsend.sendtext("<get_jobs>")
return


clicklv1:

file_selected := lv1.getselected_text()
ftproot.file_selected := get_stem(file_selected)
tcpsend.sendtext("<get_script><" . file_selected . ">")
updatestatus(ftproot.choice . ftproot.file_selected)
return

clicklv2:

file_selected := lv2.getselected_text()
tcpsend.sendtext("<get_scdata><" . file_selected . ">")

return


send_tcp:
tcpsend.sendtext("send text to python " . A_TickCount)
return






guiClose:
esc::
ExitApp



write_story(path, text)
{
	SplitPath, path, outfilename, outdir, outextension, outnamenoext, outdrive
	outfilename := A_ScriptDir . "\download\" . outnamenoext . ".txt"
	FileDelete, %outfilename%
	FileAppend, %text%, %outfilename%
}



get_stem(path)
{
	SplitPath, path, outfilename, outdir, outextension, outnamenoext, outdrive
	return outfilename
}



updatelog(text)
{
	FormatTime, logfile,, yyyy-MM-dd
	logfile := A_ScriptDir . "\log\" . "ahk_log_" . logfile . ".log"
	FormatTime, time_log,, yyyy/MM/dd HH:mm.ss
	if checklogfile(logfile)
		FileAppend, [%time_log%_%A_MSec%]  - Backup old log file .................`r`n, %logfile%
	FileAppend, [%time_log%_%A_MSec%]  - %text%`r`n, %logfile%
	FileAppend, [%time_log%_%A_MSec%]  - %text%`r`n, *
}

checklogfile(chkfile)
{
	FileGetSize, size, %chkfile%
	if (size > 3000000)
	{
		SplitPath, chkfile, outfilename, outdir, outextension, outnamenoext, outdrive
		FormatTime, outputvar,, yyyyMMdd-HHmmss
		FileMove, %chkfile%, %outdir%\%outnamenoext%_%outputvar%.%A_MSec%.%outextension%, 0
		return 1
	}
	else
		return 0

}



printobjectlist(myobject)
{
	temp := "`r`n--------   Print object list  ---------`r`n"
	for key, val in myobject
		temp .= key . " ---->  " . val . "`r`n"
	FileAppend, %temp%, *
	return temp
}


print(text)
{
	FileAppend, %text%`n, *
}

finialize_data()
{
	global htext, rdata
	print("[Force finialize..]")
	showtext := rdata.get_text()
	GuiControl, , %htext%, %showtext%
}

append(t)
{
	global rdata, htext, lv1, lv2, ftproot
	finchk := InStr(t, "<finish_transfer>")
	func_finialize := Func("finialize_data")
	SetTimer, %func_finialize%, -1000

	if InStr(t, "<start_transfer>")
	{
		print("[Start detected..]")
		rdata.clear()
		GuiControl, , %htext%
	}
	else if finchk
	{
		SetTimer, %func_finialize%, off
		newdata := SubStr(t, 1, finchk - 1)
		print("[Finish detected..]")
		print(rdata.count)
		print(t)
		showtext := rdata.get_text()
		GuiControl,, %htext%, %showtext%
		ftproot.showtext := showtext
		if (t = "`n<finish_transfer><incomelist>")
		{
			lv1.update_with_largedata(showtext)
		}

		if (t = "`n<finish_transfer><scriptlist>")
		{
			lv2.update_with_largedata(showtext)
		}
	}
	else
	{
		rdata.append(t)
	}
}


updatestatus(text)
{
	global hstatus
	GuiControl,, %hstatus%, %text%
	updatelog(text)
}

class large_text
{
	data := Object()
	count := 0
	__New()
	{
		this.data := ""
	}

	append(a)
	{
		this.data.push(a)
		this.count += 1
	}

	get_text()
	{
		result := ""
		for k, v in this.data
		{
			result .= v
		}
		return result
	}

	get_dataobj()
	{
		return this.data
	}

	clear()
	{
		this.data := Object()
		this.count := 0
	}
}



class class_tcpsend					; tcpsend class for non block tcp socket by sendust
{
	tcpclient := Object()
	;timer := ObjBindMethod(this, "disconnect")
	tick_send := A_TickCount
	ip := ""
	port := 0


	__New(ip, port)
	{
		this.ip := ip
		this.port := port
	}

	sendText(text)
	{
		updatelog("Create tcp remote class....")
		address := Object()
		address[1] := this.ip
		address[2] := this.port
		diff := A_TickCount - this.tick_send
		if (diff < 50)
			Sleep, 50											; insert short delay for non-block socket
		try
			this.tcpclient.disconnect()
		catch, err
			updatelog("error while disconnect")

		try
		{
			this.tcpclient := new SocketTCP()		; Establish tcp connection with Caspar CG Server
			this.tcpclient.Connect(address)
			this.tcpclient.onRecv := this.tcprecv
			this.tcpclient.sendtext(text)
			this.tick_send := A_TickCount
		}
		catch, err
			updatelog(printobjectlist(err))
	}

	tcprecv()
	{
		static count := 0
		text := this.RecvText(1100)

		if (StrLen(text) > 1)
		{
			count += 1
			;append(text)
		}
		updatelog("Recv count is " . count)
		updatelog(text)
		updatestatus(text)
	}
}



class class_udprecv
{
	remoteudp := Object()

	__New(ip, port)
	{
		updatelog("Create udp remote class....")
		address := Object()
		address[1] := ip
		address[2] := port
		this.remoteudp := new SocketUDP()
		this.remoteudp.Bind(address)
		this.remoteudp.onRecv := this.udprecv
	}

	udprecv()
	{
		text :=  this.RecvText(1100)
		append(text)
		;updatelog("UDP Recv " . text . "`r`n")
	}

	__Delete()
	{
		updatelog("Delete udp remote class.....")
		try
		{
			this.remoteudp.onRecv := ""
			this.remoteudp.Disconnect()
			this.remoteudp := ""
		}
		catch, err
			updatelog(printobjectlist(err))
	}
}


class c_lv
{
	hlv := Object()				; Store LV handle
	lv_col := Object()
	col_max := 0


	__New(hlv, col_max)
	{
		this.hlv := hlv
		this.col_max := col_max
	}

	addrow(obj)
	{
		handle := this.hlv
		Gui, ListView, %handle%
		result := LV_Add(, obj[1], obj[2], obj[3], obj[4], obj[5], obj[6], obj[7], obj[8], obj[9], obj[10])
		LV_ModifyCol()
		return result
	}

	update_with_largedata(data)
	{
		handle := this.hlv
		Gui, ListView, %handle%
		LV_Delete()
		ldata := Object()
		ldata := StrSplit(data, "`n", "`r")
		for k, v in ldata
		{
			eachline := StrSplit(v, "|", "`r")
			LV_Add(, k, eachline[1], eachline[2])
		}
		LV_ModifyCol()
	}

	renumber()
	{
		handle := this.hlv
		Gui, ListView, %handle%
		Loop, % LV_GetCount()
			LV_Modify(A_Index, , A_Index)
		LV_ModifyCol()
	}

	getrow(nbr)
	{
		result := Object()
		handle := this.hlv
		Gui, ListView, %handle%
		Loop, % this.col_max
		{
			LV_GetText(outputvar, nbr, A_Index)
			result[A_Index] := outputvar
		}
		;print("Get row data " . nbr)
		return result
	}

	modifyrow(nbr, arry)
	{
		handle := this.hlv
		Gui, ListView, %handle%
		;print("Modify row number " . nbr)
		result := LV_Modify(nbr, , arry[1],  arry[2],  arry[3],  arry[4],  arry[5],  arry[6],  arry[7],  arry[8],  arry[9],  arry[10])
		return result
	}

	getselected()
	{
		handle := this.hlv
		Gui, ListView, %handle%
		row_sel := LV_GetNext(0, "F")
		;print("Selected row is " . row_sel)
		return row_sel
	}

	getselected_text()
	{
		handle := this.hlv
		Gui, ListView, %handle%
		row_sel := LV_GetNext(0, "F")
		LV_GetText(outputvar, row_sel, 2)
		return outputvar


	}


	deleterow(nbr)
	{
		handle := this.hlv
		Gui, ListView, %handle%
		LV_Delete(nbr)
	}

	save(filename)
	{
		FileDelete, %filename%
		result := Object()
		handle := this.hlv
		Gui, ListView, %handle%
		max_count := LV_GetCount()
		Loop, % max_count
		{
			row_single := ""
			result := this.getrow(a_index)
			for key, val in result
			{
				if (key < this.col_max)
					delimiter := "|"
				else
					delimiter := "`n"
				row_single .= val . delimiter
			}
			;print(row_single)
			FileAppend, %row_single%, %filename%
		}
	}


	read(filename)
	{
		lv_data := Object()
		FileRead, outputvar, %A_ScriptDir%\%filename%
		Loop, Parse, outputvar, "`n", "`r"
		{
			lv_data := StrSplit(A_LoopField, "|")
			if (StrLen(lv_data[2]) > 1)
				this.addrow(lv_data)
		}

	}


}





class wget
{
	__New()
	{
		this.binary := A_WorkingDir . "\bin\wget.exe"
	}

	connect(address, port, username, password)
	{
		this.address := address
		this.port := port
		this.username := username
		this.password := password
	}

	get_file_ftp(path_remote)
	{
		url := "ftp://" . this.address . ":" . this.port
		username := " --ftp-user=" . """" . this.username . """"
		password := " --ftp-password=" . """" .  this.password  . """"

		cli := this.binary . "  " . username . password . "  " . """" . url . path_remote . """"

		wdir := A_WorkingDir . "\download"

		RunWait, %cli%, %wdir%, Min, pid
		;Clipboard := cli
		;tmr := ObjBindMethod(this, "finish_chk")
		;SetTimer,  %tmr%, -3000
	}

	get_file(path_remote)
	{
		url := "http://" . this.address . ":" . this.port

		cli := this.binary . "  " . """" . url . path_remote . """"

		wdir := A_WorkingDir . "\download"
		FileAppend, %cli%, *
		RunWait, %cli%, %wdir%, Min, pid
		;Clipboard := cli
		;tmr := ObjBindMethod(this, "finish_chk")
		;SetTimer,  %tmr%, -3000
	}



	finish_chk()
	{
		MsgBox "process finished"
	}

}