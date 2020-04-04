import click


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("Welcome to the cchat app 🥳")
        click.echo("Run contacts --help for options.")


from . import auth
