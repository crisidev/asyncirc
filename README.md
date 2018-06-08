# asyncirc [![Build Status](https://travis-ci.com/pdxjohnny/asyncirc.svg?branch=master)](https://travis-ci.com/pdxjohnny/asyncirc)

asyncio (Python 3.6+) tcp based chat server and client library. With CLI.

## Test Cases

|  TC | IRC Grading                                                   | Points |
| --- |---------------------------------------------------------------|:------:|
|  1  | RFC Document                                                  |  20    |
|  2  | Server Process                                                |  3     |
|  3  | Client can connect to a server                                |  3     |
|  4  | Client can create a room                                      |  3     |
|  5  | Client can list all rooms                                     |  3     |
|  6  | Client can join a room                                        |  3     |
|  7  | Client can leave a room                                       |  2     |
|  8  | Client can list members of a room                             |  3     |
|  9  | Multiple clients can connect to a server                      |  5     |
|  10 | Client can send messages to a room                            |  5     |
|  11 | Client can join multiple (selected) rooms                     |  10    |
|  12 | Client can send distinct messages to multiple selected rooms  |  10    |
|  13 | Client can disconnect from a server                           |  5     |
|  14 | Server can disconnect from clients                            |  5     |
|  15 | Server can gracefully handle client crashes                   |  5     |
|  16 | Client can gracefully handle server crashes                   |  5     |
|  17 | Programming Style                                             |  10    |

|  TC | IRC Grading                                                   | Points |
| --- |---------------------------------------------------------------|:------:|
|  18 | Private or Ephemeral Messaging                                |  5     |
|  19 | Secure messaging                                              |  5     |
|  20 | File transfer                                                 |  5     |
|  21 | Cloud connected server                                        |  5     |
