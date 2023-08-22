FileEncoding , UTF-8
class wininetftp
{
   __New()
   {
	   this.inet_hModule := DllCall("LoadLibrary", "str", "wininet.dll")
	   if(!inet_hModule) {
		  inet_hModule = 0
	   }
   }

   FtpConnect(Server, Port, Username, Password)
   {
		Service := "ftp"
		FtpPassive := 0

	   this.inet_hInternet := DllCall("wininet\InternetOpenW"
		  , "wstr", (Agent != "" ? Agent : A_scriptName)
		  , "UInt", (Proxy != "" ? 3 : 1)
		  , "str", Proxy
		  , "str", ProxyBypass
		  , "Ptr", 0)
	   If(!this.inet_hInternet) {
		  this.INetClose()
		  return false
	   }

	   this.hConnection := DllCall("wininet\InternetConnectW"
		  , "Ptr", this.inet_hInternet
		  , "str", Server
		  , "uint", Port
		  , "str", Username
		  , "str", Password
		  , "uint", (Service = "ftp" ? 1 : (Service = "gopher" ? 2 : 3)) ; INTERNET_SERVICE_xxx
		  , "uint", (FtpPassive != 0 ? 0x08000000 : 0) ; INTERNET_FLAG_PASSIVE
		  , "Ptr", 0)

	   return this.hConnection


	}

	FtpGetFile(RemoteFile, LocalFile="", TransferType="B", OverWrite=0, LocalAttrib=0)
	{
	   return DllCall("wininet\FtpGetFileW"
		  , "Ptr", this.hConnection
		  , "wstr", RemoteFile
		  , "wstr", (LocalFile != "" ? LocalFile : RemoteFile)
		  , "int", !OverWrite
		  , "uint", LocalAttrib
		  , "uint", (TransferType == "A" ? 1 : 2)   ; FTP_TRANSFER_TYPE_ASCII or FTP_TRANSFER_TYPE_BINARY
		  , "Ptr", 0)
	}

	FtpSetCurrentDirectory(Directory)
	{
	   return DllCall("wininet\FtpSetCurrentDirectoryW", "Ptr", this.hConnection, "wstr", Directory)
	}

	INetClose()
	{
		try
		{
			DllCall("wininet\InternetCloseHandle", "Ptr", this.inet_hInternet)
		}

		try
		{
			DllCall("FreeLibrary", "Ptr", this.inet_hModule)
		}
		this.inet_hModule := 0
		this.inet_hInternet := 0
	}

}


ftp := new wininetftp
ftp.FtpConnect("10.10.108.221", 21, "sinwoo", "3014")
ftp.FtpSetCurrentDirectory("/여러가지")
;ftp.FtpGetFile("abc.txt")
;ftp.FtpGetFile("가나다.txt")