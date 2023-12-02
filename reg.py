import click
import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args

@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
def cli():
    '''Tools for dealing with registers when doing embeded software development.
    
    Commands can be shortened to the first few characters.
    '''
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
@click.option('--field', '-f', default=[], multiple=True,
              help='Display the value of field(s), as well as the new register value including the new value for the field(s).'
                    ' E.g, "7:9=0x7,[15:12],2:2,[1]" sets [9:7] to 0x7, and display [15:12], [2], [1] at the same time')
@click.option('--narrow', '-n', 'squeeze', flag_value='narrow',
              help='Squeeze the table horizontally.')
@click.option('--narrower', '-nn', 'squeeze', flag_value='narrower',
              help='Squeeze the table more to fit a tight screen.')
@click.option('--save', '-s', is_flag=True,
              help=f'Save the result as SVG pictures in a folder. Open it with a web browser like Chrome or Firefox.')
@click.argument('value')
def regfields(value, field, squeeze, save):
    '''Get the fields in a value and set the fields given the corresponding values.
    
        Any valid number format such as decimal and hexical is supported.
    '''
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from dataclasses import dataclass
    import pprint
    from bitarray.util import int2ba
    import re

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
            ls = list(filter(None, ','.join(field).split(',')))
            logging.debug(ls)
            lss = [re.sub("[\[\]]", "", l).split('=') for l in ls]
            logging.debug(lss)
            bs = [sorted([int(i, 0) for i in bs[0].split(':')], reverse=True) for bs in lss]
            bounds = [b if len(b) > 1 else b*2 for b in bs]
            logging.debug(bounds)
            new_values = [int(bs[1], 0) if len(bs) > 1 else None for bs in lss]
            logging.debug(new_values)
            has_new = True if list(filter(None, new_values)) else False
            cs = [251, 153, 226, 190, 183, 51]
            colors = cs + [15] * (32-len(cs))
            styles = [f'bold color({colors[i]})' for i in range(len(bounds))]
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
    styles = [sty(i, fs)[0] if sty(i, fs) else 'dim' for i in indices]
    styles.reverse()
    logging.debug(styles)

    ## For the table
    paddings = {}
    match squeeze:
        case 'narrow': paddings['collapse_padding'] = True
        case 'narrower': paddings['padding'] = 0
        case _: pass

    table = Table(title='', box=box.SIMPLE_HEAD, show_lines=True, title_justify='left',
                  **paddings)
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
                    bits[i] = '[bold reverse]' + bits[i]
        bits = [b if b.startswith('[') else '[dim]' + b for b in bits]
        logging.debug(bits)
        bits.reverse()
        table.add_row(*bits)

    ## Display
    b_formatted = lambda a_s, b_s: ''.join([f'[bold reverse]{b_s[i]}[/bold reverse]' if a_s[i] != b_s[i] else b_s[i]
                                               for i in range(len(b_s))])
    val_chg_fmtted = lambda l, r, a, b: "{}{}{}".format(f'[{l}:{r}]'.ljust(7, ' ') + ' = ' if l != None and r != None else '',
                                                        a, ' --> ' + b_formatted(a, b) if b else '')

    values = [val_chg_fmtted(32-1, 0, f'0x{a:09_X}', f'0x{b:09_X}' if has_new else '')]
    values += ["{} = {}{}".format(f'[{f.limits[0]}:{f.limits[1]}]'.ljust(7, ' '),
                                    f'0x{f.value:X}', f' --> 0x{f.new_value:X}' if f.new_value else '')
                        for f in fs]
    
    group = Group(
        Panel.fit(table, title='[bold blue]Register Bits',
                    subtitle=val_chg_fmtted(None, None, f'0x{a:09_X}', f'0x{b:09_X}' if has_new else '')),
        Panel.fit('\n'.join(values), title='[bold blue]Values')
    )

    console = Console(record=True)
    console.print(group)
    if save:
        from pathvalidate import sanitize_filepath
        from pathlib import Path
        save_path = Path('reg_fileds_save')
        save_path.mkdir(parents=True, exist_ok=True)
        console.save_svg(sanitize_filepath(save_path / "Value_{}--Fields_{}.svg".format(value, field), replacement_text='_'))

if __name__ == '__main__':
    cli()
