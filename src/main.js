const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const initSqlJs = require('sql.js');

const DB_FILE_NAME = 'questions.db';
const SQL_SOURCE_FILE = 'questions_sqlite.sql';

let sqlModulePromise;
let databasePromise;

function getDevPath(...segments) {
  return path.join(__dirname, '..', ...segments);
}

function getDataPath(...segments) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'data', ...segments);
  }

  return getDevPath(...segments);
}

function getSqlWasmPath(fileName) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'sql.js', fileName);
  }

  return getDevPath('node_modules', 'sql.js', 'dist', fileName);
}

async function getSqlModule() {
  if (!sqlModulePromise) {
    sqlModulePromise = initSqlJs({
      locateFile: (file) => getSqlWasmPath(file),
    });
  }

  return sqlModulePromise;
}

async function ensureDatabaseFile() {
  const dbPath = getDataPath(DB_FILE_NAME);
  if (fs.existsSync(dbPath)) {
    return dbPath;
  }

  const sqlSourcePath = getDataPath(SQL_SOURCE_FILE);
  if (!fs.existsSync(sqlSourcePath)) {
    throw new Error(
      `Bundled question data is missing. Expected one of: ${dbPath} or ${sqlSourcePath}`
    );
  }

  const SQL = await getSqlModule();
  const sqlText = fs.readFileSync(sqlSourcePath, 'utf8');
  const db = new SQL.Database();
  db.run(sqlText);
  const buffer = Buffer.from(db.export());
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  fs.writeFileSync(dbPath, buffer);
  db.close();
  return dbPath;
}

async function getDatabase() {
  if (!databasePromise) {
    databasePromise = (async () => {
      const SQL = await getSqlModule();
      const dbPath = await ensureDatabaseFile();
      const data = fs.readFileSync(dbPath);
      return new SQL.Database(data);
    })();
  }

  return databasePromise;
}

function mapExecRows(result) {
  if (!result.length) {
    return [];
  }

  const [{ columns, values }] = result;
  return values.map((valueRow) =>
    columns.reduce((row, column, index) => {
      row[column] = valueRow[index];
      return row;
    }, {})
  );
}

function toAssetUrls(serializedPaths) {
  const paths = JSON.parse(serializedPaths || '[]');
  return paths.map((relativePath) => pathToFileURL(getDataPath(relativePath)).href);
}

async function loadQuestions() {
  const db = await getDatabase();
  const result = db.exec(
    'SELECT id, questionID, question, question_images, options, answer, explanation, explanation_images FROM questions ORDER BY id ASC'
  );

  return mapExecRows(result).map((row) => ({
    id: row.id,
    questionID: row.questionID,
    question: row.question,
    questionImages: toAssetUrls(row.question_images),
    options: JSON.parse(row.options).map((option) => ({
      ...option,
      images: (option.images || []).map((relativePath) => pathToFileURL(getDataPath(relativePath)).href),
    })),
    answer: row.answer,
    explanation: row.explanation,
    explanationImages: toAssetUrls(row.explanation_images),
  }));
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 1024,
    minHeight: 760,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.removeMenu();
  window.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

ipcMain.handle('questions:list', async () => loadQuestions());

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});