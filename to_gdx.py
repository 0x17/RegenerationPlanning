import platform
import gams
from gdx_utils import *


def convert_instance(obj, out_gdx_fn):
    dirs = {
        'Darwin': dict(system='/Library/Frameworks/GAMS.framework/Resources/',
                       workdir='/Users/andreschnabel/Desktop'),
        'Windows': dict(system='C:\\GAMS\\32',
                        workdir='C:\\Users\\Andre\\Desktop')
    }

    ws = gams.GamsWorkspace(system_directory=dirs[platform.system()]['system'],
                            working_directory=dirs[platform.system()]['workdir'])
    db = ws.add_database()

    sets = dict(i=['ngoods', 'Gueter'],
                k=['ncomponents', 'Komponenten'],
                s=['ndamagepatterns', 'Schadensbilder'],
                t=['nperiods', 'Perioden'])

    add_sets_to_database(db, obj, sets)

    params = dict(ekt=['ik', 'Ankunftszeitpunkt (ganzzahlig) von Teil i,k'],
                  eks=['ik', 'Schadensbild (ganzzahlig) von Teil i,k'],
                  eksreal=['ik', 'Tatsächliches Schadensbild (ganzzahlig) von Teil i,k'],
                  due=['i', 'Liefertermin/Frist'],
                  c=['i', 'Verspaetungskostensatz pro ZE'],
                  rd=['k', 'Remontagedauer in ZE'],
                  rc=['k', 'Reparaturkapazitaet in KE'],
                  hc=['ks', 'Lagerkostensatz pro ZE und ME in Zustand'],
                  d=['ks', 'Reparaturdauern in ZE'],
                  bd=['ks', 'Bestelldauer in ZE'],
                  bc=['ks', 'Bestellkostensatz pro ME in Zustand s von Komponente k'])

    add_params_to_database(db, obj, params)

    db.export(out_gdx_fn)


if __name__ == '__main__':
    import generator

    inst = generator.generate_instance(1, 2, 3, 3, 300)
    convert_instance(inst, 'myinst.gdx')
