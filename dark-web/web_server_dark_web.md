### STEP 0: FUNCTIONAL TOR
   ```bash
   sudo apt install tor
   sudo systemctl enable tor deb.torproject.org-keyring
   ```
   - Arch linux
    ```bash
    sudo pacman -Syu tor
    ```

### STEP 1: GET A WEB SERVER WORKING

- Apache
```bash
sudo apt install apache2
```
- Nginx
```bash
sudo apt install nginx
```
### STEP 2: CONFIGURE YOUR TOR ONION SERVICE

--- Open the torrc file
--- Add the following lines
```bash
HiddenServiceDir /var/lib/tor/my-website/
HideenServicePort 80 127.0.0.1:80
```

### STEP 3: RESTART TOR AND CHECK THAT IT WORKED
```bash
sudo systemctl restart tor
```
### STEP 4: TEST THAT YOUR ONION SERVICE WORKS

--- hostname file in the HiddenServiceDir

