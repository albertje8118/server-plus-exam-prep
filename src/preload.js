const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('examApi', {
  listQuestions: () => ipcRenderer.invoke('questions:list'),
});