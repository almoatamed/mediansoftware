# communication protocol:
	- is a small communication software which works as intermediate stage between main system and the medical instrument,
	  the intermediate process is as follow.
	- depending on the operating medium between the software and the medical instrument Where Usually there are two types
	  of medium TCP/IP or network connection, and serial port connection. For this case. The user can choose either the IP
	  of the Local host or the serial port connection.
	- Choose the file location were results and protocol registries are saved. (default location is Desktop)
	- Press CONNECT which will open up the port and will start a communication process as follow.
		- The software waits for a result to be received from medical instrument.
		- if a result is received the data is then decoded, and saved in a file
		   named after the patient ID which is included in the received results.
        	   Then the same patient ID is saved in a file named Unwritten Results which is then
                   written to the main system through Database credentials.
	- In case an error arises or disconnection, DISCONNECT will be initiated automatically.
	- In case a manual disconnection is required, press DISCONNECT.
	- status box displays if connected or not, if results were received,
	  if error occured, if query happened, in general manner the status box display process history.
