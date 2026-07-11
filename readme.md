# Introduction
This is a file encryption tool capable of encrypting files of all types. It has a notable Vibe-coding flavor—30% of the code was written by Yuanbao (many thanks to Yuanbao for that), while the remaining 70% is my own work. Nearly all testing and bug fixes were also handled by me.

# Installation & Usage
Install Python and required dependencies on your target Linux machine, then download the source code to run the tool.  
It has been tested on Ubuntu. CLI system dependencies are as follows:
```bash
sudo apt install 7zip poppler-utils python3-gi-cairo libpango1.0-dev libcairo2-dev fuse libfuse-dev
```
Python dependencies can be installed via pip:
```bash
pip install pycairo pdf2image opencv-python fusepy argon2-cffi pillow
```

For the GUI, additional dependencies are required:
```bash
sudo apt install python3-tk xclip
pip install tkinterdnd2 ttkbootstrap pyperclip
```

# Interface
The GUI is built with `tkinter` and styled using `ttkbootstrap` for visual polish.

# Internal Working Principles & Design
## Principles
1. Prompt the user for the file to encrypt and the password.
2. Generate a random internal `salt`, then derive the user key using the `argon2id` algorithm (chosen for its extremely high security) to produce a derived key noted as `user_password`.
3. Generate another random internal password, noted as `file_password`.
4. Create a 7z archive and store `file_password` encrypted with `user_password` inside the archive.
5. Generate a preview image for the file to be encrypted, then split the file into chunks. The recommended chunk size is `10 MB`.
6. Encrypt and compress each chunk using `file_password`; the preview image is encrypted and compressed in the same way.
7. Write the chunk size, number of chunks and internal `salt` into `metadata` and place it in the archive (stored unencrypted).
8. Write the original filename, creation/access/modification timestamps, and any additional metadata the user wishes to include into `original_metadata`, then encrypt this data with `user_password`.
9. When the user wants to open the file, the tool decrypts it first, then mounts a `FUSE` filesystem to present the decrypted file to upper-layer applications.
10. Files are never fully loaded into memory at once. Instead, based on the requested read offset and length, the tool locates the relevant chunk(s), loads them into memory, and returns the requested data to the upper layer.
11. Optional: Users can choose to generate recovery data. If enabled, `par2` is used to add redundancy to the archive; a recovery ratio of `15%` is recommended.

## Design Considerations
1. 7z container: 7z archives offer strong security and are resistant to known-plaintext attacks, making them the ideal choice for the encrypted container format.
2. Argon2id key derivation: Even if the archive is accidentally leaked, the use of Argon2id makes brute-force attacks extremely difficult, providing robust protection even when the original password is weak.
3. Dual-password design: File encryption uses an internally generated random `file_password`. When users need to change the access password, only `file_password` needs to be re-encrypted. There is no need to re-encrypt everything, significantly improving efficiency.
4. FUSE memory mapping: Using a `FUSE` filesystem ensures that data never touches the disk; everything resides in memory. Once the filesystem is unmounted, the file becomes unrecoverable. If the computer shuts down unexpectedly, the data is wiped immediately, preventing residual files from lingering on the hard drive (though data may still persist in the `swap` partition).
5. On-demand loading & caching: Only the currently requested data blocks are loaded, avoiding OOM errors when opening large files. Users can configure the cache size to keep frequently used chunks in memory, significantly improving read performance.
6. Recovery data: Redundancy checks improve the archive’s fault tolerance against storage media corruption.

# File Structure & Internal Mechanism Details
## CLI Tools
### `creator.py`
Reads the file to be encrypted and creates an encrypted archive.  
Parameters:  
- `input`: Path to the file to encrypt
- `output`: Output path for the encrypted file
- `password`: Encryption password
- `-c`/`--chunk_size`: Chunk size in bytes; defaults to `2MB` if not specified
- `-r`/`--recovery`: Set the percentage of redundant recovery data to generate (range: 0–100)
- `-m`/`--metadata`: Add extra metadata in JSON format
- `-y`/`--yes`: Auto-answer "yes" to all interactive prompts, skipping confirmation questions

### `mounter.py`
Reads an encrypted archive, decrypts it, and mounts a `FUSE` filesystem to provide access to the data.  
Parameters:  
- `archive`: Path to the encrypted archive
- `password`: Password for decryption
- `mountpoint`: System mount point for the decrypted filesystem
- `-f`/`--filename`: Override the filename read from metadata; specify a custom filename
- `-c`/`--cachesize`: Cache size in bytes; defaults to `10MB`
- `-o`/`--openfile`: Automatically open the target file after mounting completes

### `meta_editor.py`
Modifies file metadata and passwords.  
Parameters:  
- `archive`: Path to the archive to edit
- `password`: Access password for the archive
- `data`: Target metadata field to modify
- `new`: New value to assign to the selected field

### `repair.py`
Checks and repairs corrupted files.  
Parameters:  
- `-d`/`--directory`: Repair all files in the specified directory
- `-f`/`--file`: Repair only the specified single file

## Custom Libraries
### `passwordutil.py`
Provides password derivation and random salt generation based on Argon2id.  
Functions:  
- `passwordutil.rand(length=32)`: Generates a hexadecimal random string; default length is 32 characters
- `passwordutil.hash(password,salt)`: Hashes a password with the provided salt

### `preview.py`
Generates preview images for files to be encrypted.  
Functions:  
- `preview.preview(file_path,quality=100,max_width=960,max_height=540)`: Generate a preview image for a given file

### `sevenzipwrapper.py`
Archive handling utility wrapping the 7z command-line tool.  
Functions:  
- `read_file(archive, filename, password=None)`: Read a file from an archive
- `write_file(archive, filename, data, password=None)`: Write a file into an archive

## Configuration File
### `config.json`
Stores configuration settings.  
Keys:  
- `mounter_path`: Default path for encrypted archives
- `creator_path`: Default output path for encrypted files
- `rec`: Default recovery data ratio
- `chunk_size`: Chunk size
- `tags`: Default tags
- `password`: Default password
- `default_chunk_size`: Default chunk size

## GUI Tools
### `creator_gui.py`
GUI wrapper for `creator.py`, used to generate encrypted archives.

### `mounter_gui.py`
Provides file previews and integrates repair, decryption, and other features for easier user operation.

# Acknowledgments
Special thanks to:  
1. All developers who built the excellent libraries used in this project!
2. Yuanbao, for writing 30% of the code and laying the foundation for this project.
3. Icons8, for providing the beautiful icons.
