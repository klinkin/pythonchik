import nox


@nox.session(python=["3.12"])
def tests(session):
    session.install("pytest")
    session.install("-e", ".")
    session.run("pytest", "tests/")
