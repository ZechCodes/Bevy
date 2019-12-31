# Exo

Web framework designed to keep it simple, built to run on Starlette.

## Example

```py
import exo


@exo.uses("users", "session")
class MyWebsite(exo.Page):
    @exo.route("/", name="home")
    def index(self):
        return self.template(
            "templates.home",
            title="Welcome!!!"
        )
    
    @exo.route("/login", name="login")
    def login(self):
        return self.template("templates.login")
        
    @login.context(method="post")
    @login.validator("login")
    def login(self, username, password):
        user = self.users.get_user(username)
        if user.password_matches(password):
            self.session.create(user)
            return self.context.redirect(self.routes.home)
        return self.context.env(login="failed")
    
    @exo.validator("login")
    def login_validator(self, form):
        if {"username", "password"} not in form:
            form.failed(invalid=["username", "password"])
        return form.username, form.password
```

