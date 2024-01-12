const express = require('express');
const app = express();
const http = require('http').Server(app);
// const http = require('http').Server(app);
const io = require('socket.io')(http);
const serveIndex = require('serve-index')

const cloudcmd = require('cloudcmd');
const sio_server = require('socket.io').Server;


const port = 50080;
const prefix = '/fm';



const socket = new sio_server(http, {
	path: `${prefix}socket.io`,
});

const config = {
    name: 'cloudcmd :)',
	root: '\\',
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


/*
app.get('*', function(req, res){
        updatelog("get request...  " + req.socket.remoteAddress);
});
*/


io.on('connection', function(socket){
   // console.log('A user connected');
   updatelog('A user connected');
/*	
	socket.onAny(()=>{
		console.log(`any socket event`)
	});
  */
  
   // Send a message when
   socket.on('disconnect', function () {
        // console.log('A user disconnected');
        updatelog('A user disconnected');
   });
   
   
   socket.on('msg_reuter', (data)=>{
        socket.broadcast.emit("engine_reuter", data);
        // console.log(data);
        updatelog("[msg_reuter] ---> [engine_reuter]");
    });
    
	

	socket.on('msg_engine', (data)=>{
        socket.broadcast.emit("msg_engine", data);
        // console.log(data);
        updatelog("[msg_engine] ---> [msg_engine]");
    });
	
	
	socket.on('rep_engine', (data)=>{
	socket.broadcast.emit("rep_engine", data);
	// console.log(data);
	updatelog("[rep_engine] ---> [rep_engine]");
    });

    socket.on('msg_aptn', (data)=>{
        socket.broadcast.emit("engine_aptn", data);
        // console.log(data);
        updatelog("[msg_aptn] ---> [engine_aptn]");
    });
    
    
    socket.on('msg_cnn', (data)=>{
        socket.broadcast.emit("engine_cnn", data);
        // console.log(data);
        updatelog("[msg_cnn] ---> [engine_cnn]");
    });

   socket.on('msg_gui', (data)=>{
        socket.broadcast.emit("msg_gui", data);
        console.log(data);
        updatelog("[msg_gui] <--- [msg_gui]");
    });


});


http.listen(port, function(){
   // console.log('listening on localhost:3000');
   updatelog(`listening on localhost:${port}`);
});


function updatelog(text){
    now = new Date().toISOString();
    console.log(now + " " + text);
}

setTimeout(()=>{console.log(`listening on localhost:${port}`)}, 2000)
