# Bevy.App
Bevy.App is an app framework built on the  [Bevy](https://github.com/ZechCodes/Bevy) dependency injection framework. The goal of Bevy.App is to provide a convenient infrastructure that allows for easy configuration, extension, and observation. 

Bevy.App provides a configurable boostrap along with an extension system. It uses [Bevy.Config](https://github.com/ZechCodes/Bevy/tree/main/bevy/config) and [Bevy.Events](https://github.com/ZechCodes/Bevy/tree/main/bevy/events) to allow for easy configuration and simple observability without requiring tight coupling.

## Installation
```shell script
pip install bevy.app
```

**Usage**

Using Bevy.App is as simple as creating a project directory that contains an `app.settings.json` and all the modules and packages you'd like to have loaded as extensions. Inside your `app.settings.json` you will list the module names of the extension files you'd like loaded as keys of a mapping, the values will be a boolean indicating if it should be enabled or disabled.
```json
{
  "extensions": {
    "app": true,
    "api_service": true
  }
}
```
Any objects in your extension modules that should be created by the app need to inherit from `bevy.app.Extension`.
```python
from bevy.app import Extension

class AppExtension(Extension):
    ...
```
The app can be started by running the `bevy.app` module inside the directory that has your `app.settings.json` file.
```shell
python -m bevy.app
```
