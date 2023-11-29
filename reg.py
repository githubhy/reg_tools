import click
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

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
@click.option('--field', default='',
              help='Display the value of field(s), as well as the new register value including the new value for the field(s). '
                    'e.g, 7:9=0x7,15:12,2:2,1 will set [9:7] to 0x7, and display it as well as [15:12], [2], [1]')
@click.argument('value')
def regfields(field, value):
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from dataclasses import dataclass
    import pprint
    from bitarray import bitarray
    from bitarray.util import int2ba

    pp = pprint.PrettyPrinter(indent=4)

    a = int(value, 0) # auto conversion

    @dataclass
    class Field():
        limits: list
        style: str
        value: int
        new_value: int

    try:
        fs = []
        has_new = False
        logging.debug(field)
        if field:
            ls = list(filter(None, field.split(',')))
            logging.debug(ls)
            lss = [l.split('=') for l in ls]
            logging.debug(lss)
            bs = [sorted([int(i, 0) for i in bs[0].split(':')], reverse=True) for bs in lss]
            bounds = [b if len(b) > 1 else b*2 for b in bs]
            logging.debug(bounds)
            new_values = [int(bs[1], 0) if len(bs) > 1 else None for bs in lss]
            logging.debug(new_values)
            has_new = True if list(filter(None, new_values)) else False
            cs = [251, 153, 226, 190, 183, 51]
            colors = cs + [15] * (32-len(cs))
            styles = [f'black on color({colors[i]})' for i in range(len(bounds))]
            logging.debug(styles)
            values = [(a >> b[1]) & ((0x1 << (b[0]-b[1]+1)) - 1) for b in bounds]

            for i in range(len(bounds)):
                fs.append(Field(limits=bounds[i], style=styles[i], value=values[i], new_value=new_values[i]))

            fs = sorted(fs, key=lambda x: x.limits[0], reverse=True)

            if has_new:
                b = a
                for f in fs:
                    if f.new_value != None:
                        mask = (0x1 << (f.limits[0] - f.limits[1] + 1)) - 1
                        logging.debug(mask)
                        b = (b & ~(mask << f.limits[1])) | ((f.new_value & mask) << f.limits[1])

    except Exception as e:
        click.echo(f'REG_FIELD ERROR: {e}')


    indices = list(reversed(range(32)))
    logging.debug(indices)
    sty = lambda i, fs: list(filter(None, [f.style if f.limits[0] >= i >= f.limits[1] else None for f in fs]))
    styles = [sty(i, fs)[0] if sty(i, fs) else '' for i in indices]
    styles.reverse()
    logging.debug(styles)

    ## For the table
    table_title = f'Value: 0x{a:09_X}'
    if has_new:
        table_title = 'Original ' + table_title + f', New Value: 0x{b:09_X}'

    table = Table(title=table_title, title_style='bold white on black', box=box.HORIZONTALS)
    for i in indices:
        table.add_column(f'{i}', justify="right", style=styles[i], no_wrap=True)
    table.add_row(*int2ba(a, length=32).to01())
    logging.debug(int2ba(a, length=32).to01())

    if has_new:
        bits = list(int2ba(b, length=32).to01())
        bits.reverse()
        for i in indices:
            for f in fs:
                if (f.new_value != None) and (f.limits[0] >= i >= f.limits[1]):
                    bits[i] = '[bold white on black]' + bits[i]
        bits = [b if b.startswith('[') else '[dim]' + b for b in bits]
        logging.debug(bits)
        bits.reverse()
        table.add_row(*bits)

    console = Console()
    console.print('')
    console.print(table)

    for f in fs:
        console.print(f'[{f.limits[0]}:{f.limits[1]}] = 0x{f.value:X}{f" --> 0x{f.new_value:X}" if f.new_value else ""}')


if __name__ == '__main__':
    cli()
