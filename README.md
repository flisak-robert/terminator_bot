# terminator_bot

Known issue:

When two users are trying to book an appointment at the same time, captcha is being resolved for one user only. The other user is in a queue and (most likely) there will be timeout exception raised for captcha resolving. Captcha resolving task is in a while loop so eventually this captcha will be resolved (I think), but the user is not getting any feedback and would obviously assume that the bot is not working. Some messages could be added like (please wait as our captcha resolving solution is busy).
