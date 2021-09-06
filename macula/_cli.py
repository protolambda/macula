import click


@click.group()
def cli():
    """Macula - optimistic rollup tech for ethereum
    Contribute here: https://github.com/protolambda/macula
    """


@cli.command()
def gen():
    click.echo('generating fraud proof')
    # TODO


@cli.command()
def verify():
    click.echo('verifying fraud proof')
    # TODO
