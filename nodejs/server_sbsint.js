var express = require('express');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
//var serveIndex = require('serve-index')



app.get('/', function(req, res){
        res.sendFile(__dirname + '/gui.html');
});

app.get('*', function(req, res){
        updatelog("get request...  " + req.socket.remoteAddress);
});


//app.use('/log', express.static('log'), serveIndex('log', {'icons': true}))
//app.use('/image', express.static('image'), serveIndex('image', {'icons': true}))

app.use('/reuters', express.static('e:/int_download'))


io.on('connection', function(socket){
   // console.log('A user connected');
   updatelog('A user connected');
   
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



http.listen(50080, function(){
   // console.log('listening on localhost:3000');
   updatelog('listening on localhost:50080');
});


function updatelog(text){
    now = new Date().toISOString();
    console.log(now + " " + text);
}