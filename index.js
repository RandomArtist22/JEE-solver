const express = require('express');
const { spawn } = require('child_process');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const dotenv = require('dotenv');
const { v4: uuidv4 } = require('uuid');

dotenv.config();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, './uploads/');
  },
  filename: function (req, file, cb) {
    const uniqueFilename = uuidv4() + path.extname(file.originalname);
    cb(null, uniqueFilename);
  },
});

const upload = multer({
  storage: storage,
  limits: {
    fileSize: 5 * 1024 * 1024, // 5MB file size limit
  },
  fileFilter: (req, file, cb) => {
    const allowedMimeTypes = ['image/jpeg', 'image/png', 'image/gif'];
    if (allowedMimeTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only jpeg, png and gif are allowed.'), false);
    }
  },
});

const app = express();
app.use(express.static(path.join(__dirname, '.')));
const port = 3002;

// Function to run the Python script
async function runPythonScript(imagePath, hyperbolicApiKey, openRouterApiKey) {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python', ['OCR.py', imagePath, hyperbolicApiKey, openRouterApiKey], {
      encoding: 'utf8',
    });

    let output = '';
    pythonProcess.stdout.on('data', (data) => {
      output += data;
    });

    let errorOutput = '';
    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data;
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const parsedOutput = JSON.parse(output);
          resolve(parsedOutput);
        } catch (parseError) {
          reject(new Error(`Failed to parse Python script output: ${parseError.message}`));
        }
      } else {
        reject(new Error(`Python script failed with code ${code}. Error: ${errorOutput}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to start Python script: ${error.message}`));
    });
  });
}

app.post('/upload', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).send('No file uploaded or invalid file');
    }

    const imagePath = req.file.path;
    const hyperbolicApiKey = process.env.HYPERBOLIC_API_KEY;
    const openRouterApiKey = process.env.OPENROUTER_API_KEY;

    const output = await runPythonScript(imagePath, hyperbolicApiKey, openRouterApiKey);
    fs.promises.unlink(imagePath); // Delete the temp file asynchronously

    if (output.error) {
      return res.status(500).send(output.error);
    }

    res.send(output);
  } catch (error) {
    console.error('Error processing image:', error);
    res.status(500).send(error.message);
  }
});

app.get('/', (req, res) => {
  try {
    res.sendFile(__dirname + '/index.html');
  } catch (error) {
    console.error(error);
    res.status(500).send(error.message);
  }
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});