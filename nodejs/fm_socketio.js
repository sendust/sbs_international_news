

http = require('http');
cloudcmd = require('cloudcmd');
Server = require('socket.io').Server;
express = require('express');
const serveIndex = require('serve-index')
const cors = require('cors');

const app = express();
const port = 50080;

const http_server = http.createServer(app);
const prefix = '/fm'

const io = require('socket.io')(http_server,{
	cors:{
		origin:"*",
		methods:["GET","POST"]
	}
});

const socket = new Server(http_server, {
    path: `${prefix}/socket.io`,
	maxHttpBufferSize: 998		// Change default size (1MB => 5MB 2023/10/26)
});

const config = {
    name: 'cloudcmd :)',
};

const filePicker = {
    data: {
        FilePicker: {
            key: 'key',
        },
    },
};

// override option from json/modules.json
const modules = {
    filePicker,
};

const {
    createConfigManager,
    configPath,
} = cloudcmd;

const configManager = createConfigManager({
    configPath,
});


io.on('connection', function(socket){
    updatelog('A user connected    ' + socket.id);
    socket.emit('askForUserId');
    /*	
    socket.onAny(()=>{
        console.log(`any socket event`)
    });
    */
	  
	  socket.on("connect_error", (err) => {
	  updatelog.log(`connect_error due to ${err.message}`);
	});
	  
  
    // Send a message when
    socket.on('disconnect', function () {
        // console.log('A user disconnected');
        updatelog('A user disconnected');
    });
   
    socket.on('userIdReceived', (userId) => {
    updatelog("user ID Received... " + userId);
    });


	socket.on('msg_engine', (data)=>{
        socket.broadcast.emit("msg_engine", data);
        // console.log(data);
        updatelog("[msg_engine] ---> [msg_engine]");
        // console.dir(data);
    });
	
	
	socket.on('reply_engine', (message)=>{
        socket.broadcast.to(message.receiverId).emit('reply_engine', message.data);
        updatelog("[reply_engine] ---> [reply_engine]");
        // console.log(message)
    });


   socket.on('msg_gui', (data)=>{
        socket.broadcast.emit("msg_gui", data);
        updatelog("[msg_gui] <--- [msg_gui]");
        console.dir(data);
    });


});

app.use(cors({
    origin: '*', // 모든 출처 허용 옵션. true 를 써도 된다.
}));

app.use(prefix, cloudcmd({
    socket, // used by Config, Edit (optional) and Console (required)
    config, // config data (optional)
    modules, // optional
    configManager, // optional
}));



app.get('/debug', function(req, res){
        res.sendFile(__dirname + '/debug_gui.html');
});



app.use('/reuters', express.static('D:\\agent_REUTERS'));
app.use('/aptn',  express.static('D:\\agent_APTN'));
app.use('/cnn',  express.static('D:\\agent_CNN'));
app.use('/gui',  express.static(__dirname + '\\html'));

app.use('/log', express.static('C:\\sbsint\\log'), serveIndex('C:\\sbsint\\log', {'icons': true}))



http_server.listen(port, function(){
   // console.log('listening on localhost:3000');
   updatelog(`listening on localhost:${port}`);
});


function updatelog(text){
    now = new Date().toISOString();
    console.log(now + " " + text);
}
