

http = require('http');
cloudcmd = require('cloudcmd');
Server = require('socket.io').Server;
express = require('express');



const app = express();
const port = 1337;

const http_server = http.createServer(app);
const socket = new Server(http_server, {
    path: `/socket.io`,
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

app.use('/', cloudcmd({
    socket, // used by Config, Edit (optional) and Console (required)
    config, // config data (optional)
    modules, // optional
    configManager, // optional
}));

http_server.listen(port);