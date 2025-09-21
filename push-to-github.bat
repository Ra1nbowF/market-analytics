@echo off
echo Adding GitHub remote...
git remote add origin https://github.com/Ra1nbowF/market-analytics.git

echo Pushing to GitHub...
git branch -M main
git push -u origin main

echo Done! Your code is now on GitHub.
echo Repository URL: https://github.com/Ra1nbowF/market-analytics
pause