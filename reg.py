import click

@click.group()
def cli():
    pass


@cli.command()
@click.option('--index', default=0, help='index of VGA gain table')
@click.argument('dac_code_hex')
def dac2logic(index, dac_code_hex):
    a = int(dac_code_hex, 0)
    mask = 0x3f
    offset = 0 if not index % 2 else 12
    dac_iq = a >> offset
    dac_i = dac_iq & mask
    dac_q = (dac_iq >> 6) & mask
    val = ((dac_q << 1) << 7) | (dac_i << 1)
    click.echo("RX_LOGIC[13:0]={}".format(hex(val)))


@cli.command()
@click.option('--bits', default='0:0,1:1', help='bits range')
@click.argument('reg_val')
def regfield(bits, reg_val):
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from dataclasses import dataclass
    import pprint

    pp = pprint.PrettyPrinter(indent=4)

    a = int(reg_val, 0) # auto conversion

    @dataclass
    class Field():
        limits: list
        style: str
        value: int

    try:
        bounds = [[int(i, 0) for i in bs.split(':')] for bs in bits.split(',')]
        colors = [251, 153, 226, 190, 183, 51] + [15] * (32-6)
        # pp.pprint(colors)
        styles = [f'black on color({colors[i]})' for i in range(len(bounds))]
        values = [(a >> b[1]) & ((0x1 << (b[0]-b[1]+1)) - 1) for b in bounds]

        fields = []
        for i in range(len(bounds)):
            fields.append(Field(limits=bounds[i], style=styles[i], value=values[i]))
            click.echo(f'VAL[{bounds[i][0]}:{bounds[i][1]}] = 0x{values[i]:X}')
    except Exception as e:
        click.echo(f'REG_FIELD ERROR: {e}')
    
    table = Table(title=f'0x{a:09_X}', box=box.HORIZONTALS, pad_edge=False)

    r = reversed(range(32))
    l = []
    fields
    for i in r:
        style = ''
        for f in fields:
            if i <= f.limits[0] and i >= f.limits[1]:
                style = f.style
        table.add_column(f'{i}', justify="right", style=style, no_wrap=True)
        l.append(str((a >> i) & 0x1))
    table.add_row(*l)
    console = Console()
    console.print(table)


if __name__ == '__main__':
    cli()
