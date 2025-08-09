
Kivy Trading Simulator - Android (Stage A)

This project contains a Kivy-based Android trading simulator (offline simulation).
Files included:
- main.py           -> Kivy app
- requirements.txt  -> Python requirements (kivy)
- buildozer.spec    -> Buildozer config to build APK/AAB
- icon.png          -> placeholder icon

How to build (recommended via Docker or Linux):
1. Install Buildozer (see official docs) OR use Docker image.
2. In project folder run:
   buildozer android debug
   or for release:
   buildozer android release

Docker quick method (Linux/WSL recommended):
1. Install Docker.
2. Run a buildozer container (example):
   docker run --rm -v $(pwd):/home/user/hostcwd -w /home/user/hostcwd kivy/buildozer sh -c "buildozer android debug"

Notes:
- To publish to Play Store, generate a signing key and build an AAB (buildozer android release).
- Replace icon.png with a 512x512 production icon before publishing.
