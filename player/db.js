/*
 * Browser-side replacement for the Electron preload + main DB-loading flow.
 *
 * The Electron app exposes `window.examApi.listQuestions()` via preload and
 * answers with parsed questions whose image paths have been turned into file://
 * URLs by the main process. This shim does the same job using fetch + sql.js
 * so the renderer (src/renderer/app.js) can stay untouched.
 */
(function () {
  const PLAYER_ROOT = new URL('.', window.location.href).href;

  function resolveAssetPath(relativePath) {
    if (!relativePath) return relativePath;
    // Relative paths in the DB are stored as POSIX paths. The web player
    // ships the question bank in the same directory tree, so we just join
    // the player root with the stored relative path.
    return new URL(relativePath.replace(/^\/+/, ''), PLAYER_ROOT).href;
  }

  function resolveAssetList(serializedPaths) {
    let list = [];
    try {
      list = JSON.parse(serializedPaths || '[]');
    } catch (error) {
      console.warn('Failed to parse image list', error);
      return [];
    }
    return list.map(resolveAssetPath);
  }

  async function loadDatabase() {
    if (!window.initSqlJs) {
      throw new Error(
        'sql.js loader is missing — make sure sql-wasm.js is loaded before db.js'
      );
    }

    const SQL = await window.initSqlJs({
      locateFile: (file) => new URL(file, PLAYER_ROOT).href,
    });

    const response = await fetch(new URL('questions.db', PLAYER_ROOT));
    if (!response.ok) {
      throw new Error(
        `Failed to download questions.db (HTTP ${response.status}). ` +
          'The web player needs questions.db alongside index.html.'
      );
    }
    const buffer = new Uint8Array(await response.arrayBuffer());
    return new SQL.Database(buffer);
  }

  function rowsFromExec(result) {
    if (!result || !result.length) return [];
    // db.exec() returns an array of result sets — each set is an object with
    // {columns, values} keys, not an array. Destructure the object directly.
    const { columns, values } = result[0];
    return values.map((valueRow) =>
      columns.reduce((row, column, index) => {
        row[column] = valueRow[index];
        return row;
      }, {})
    );
  }

  async function listQuestions() {
    const db = await loadDatabase();
    try {
      const result = db.exec(
        'SELECT id, question, question_images, options, answer, explanation, explanation_images ' +
          'FROM questions ORDER BY id ASC'
      );

      return rowsFromExec(result).map((row) => ({
        id: row.id,
        question: row.question,
        questionImages: resolveAssetList(row.question_images),
        options: JSON.parse(row.options).map((option) => ({
          ...option,
          images: (option.images || []).map(resolveAssetPath),
        })),
        answer: row.answer,
        explanation: row.explanation,
        explanationImages: resolveAssetList(row.explanation_images),
      }));
    } finally {
      db.close();
    }
  }

  window.examApi = { listQuestions };
})();