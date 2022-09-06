# Prism

![Using Prism](./images/in_queue.png)

## Description
Prism is an open source stats overlay for Hypixel Bedwars (not associated).
Prism will detect the players in your lobby as they join and when you type `/who`, and automatically show you their stats.
The overlay can be extended with the [Antisniper API](https://antisniper.net) (not associated) to denick some nicked players and display estimated winstreaks.

## Qualities
- Automatic party and lobby detection
- Good players sorted to the top and highlighted in red
- Fast
- Denicking (with Antisniper API)
- Winstreak estimates (with Antisniper API)

## Tips
- Enable autowho so you don't have to type `/who` when you join a filled queue
- Follow the instructions in the settings page to add an Antisniper API key to get denicking and winstreak estimates
- Click on the pencil next to a nicked teammate to set their username

## Safety
Being open source, anyone can look at the source code for Prism to see that nothing nefarious is happening.
The released binaries are created using `pyinstaller` in GitHub Actions and uses a clean clone of the repository.
If you do not trust the released binary you can clone the project and run it locally using `python prism_overlay.py` from the project root.
