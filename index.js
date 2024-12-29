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
        fileSize: 5 * 1024 * 1024,  // 5MB file size limit
    },
    fileFilter: (req, file, cb) => {
        const allowedMimeTypes = ['image/jpeg', 'image/png', 'image/gif'];
        if (allowedMimeTypes.includes(file.mimetype)){
            cb(null, true);
        }else{
            cb(new Error("Invalid file type. Only jpeg, png and gif are allowed."), false);
        }
    }
});

const app = express();
app.use(express.static(path.join(__dirname, '.')));
const port = 3002;

// Function to run the Python script
async function runPythonScript(imagePath, hyperbolicApiKey, openRouterApiKey) {
  try {
    const pythonProcess = spawn('python', ['OCR.py', imagePath, hyperbolicApiKey, openRouterApiKey], { encoding: 'utf8' });

    let output = '';
    for await (const chunk of pythonProcess.stdout) {
      output += chunk;
    }

    let errorOutput = '';
    for await (const chunk of pythonProcess.stderr){
      errorOutput += chunk;
    }


    return new Promise((resolve, reject) => {
       pythonProcess.on('close', (code) => {
         if (code === 0) {
            resolve(output);
        } else {
             console.error("Python script error output: ", errorOutput);
            reject(new Error(`Python script failed with code ${code}`));
        }
       });
    });
  } catch (error) {
    console.error(error);
    throw error;
  }
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
    fs.promises.unlink(imagePath) //Delete the temp file asynchronously
     res.send(output);
  }
  catch (error){
     console.error("Error processing image:", error);
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