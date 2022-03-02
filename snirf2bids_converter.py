# To convert a given folder containing snirf files to BIDS folder directory with necessary files
import numpy as np
import json
from pysnirf2 import Snirf
import csv


def _getdefault(fpath, key):
    file = open(fpath)
    fields = json.load(file)

    return fields[key]


def _pull_label(fpath, field):
    # function for pulling info values from filename if it is BIDS compliant
    if fpath is None:
        return None
    fname = fpath.split('/')[-1]
    if field not in fname:
        # if the info is not even mentioned in the file name
        return None
    else:
        # if it is mentioned in the filename
        info = fname.split('_')
        for i in info:
            if field in i:
                if np.size(i.split(field)) == 1:
                    return None
                else:
                    return i.split(field)[1]
                    # need to get rid of non-alphanumeric for task name


def _check_empty_field(info):
    # Check empty fields to make sure required is filled, and optional is filled if wanted by user.
    for i in list(info.keys()):
        if i == 'sub-' and info[i] is None:
            print('Subject number is REQUIRED. Please input subject number: ')
            info[i] = input()
        elif i == 'task-' and info[i] is None:
            print('Task name is REQUIRED. Please input task name: ')
            info[i] = input()
        elif i == 'ses-' and info[i] is None:
            print('Session number is OPTIONAL. Would you like to input a number?: [y/n]')
            ans = input()
            if ans == 'y':
                print('Please input session number: ')
                info[i] = input()
            else:
                pass
        elif i == 'run-' and info[i] is None:
            print('Run number is OPTIONAL. Would you like to input a number?: [y/n]')
            ans = input()
            if ans == 'y':
                print('Please input session number: ')
                info[i] = input()
            else:
                pass
    return info


def _makefiledir(info, classname, fpath):
    if info is not None:
        filename = ""
        for name in info:
            if info[name] is not None:
                filename = filename + name + info[name] + '_'
        filename = filename + classname
        filedir = fpath + '/' + filename
    else:
        filedir = fpath + classname

    return filedir


class Field:
    def __init__(self, val):
        self._value = val

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val


class String(Field):

    def __init__(self, val):
        super().__init__(val)
        self._type = str

    @staticmethod
    def validate(val):
        if type(val) is str or val is None:
            return True


class Number(Field):

    def __init__(self, val):
        super().__init__(val)
        self.type = int

    @staticmethod
    def validate(val):
        if type(val) is not str or val is None:
            return True


class Metadata:
    """ Metadata File Class

    Class object that encapsulates the JSON and TSV Metadata File Class

    """

    def __init__(self):
        default_list, default_type = self.default_fields()
        default = {'path2origin': String(None)}
        for name in default_list:
            # assume they are all string now
            if default_type[name] == 'String':
                default[name] = String(None)
            elif default_type[name] == 'Number':
                default[name] = Number(None)

        self._fields = default
        self._source_snirf = None

    def __setattr__(self, name, val):
        if name.startswith('_'):
            super().__setattr__(name, val)

        elif name in self._fields.keys():
            if self._fields[name].validate(val):
                self._fields[name].value = val
            else:
                raise ValueError("Incorrect data type")

        elif name not in self._fields.keys():
            if String.validate(val):  # Use our static method to validate a guy of this type before creating it
                self._fields[name] = String(val)
            elif Number.validate(val):
                self._fields[name] = Number(val)
            else:
                raise ValueError('invalid input')

    def __getattr__(self, name):
        if name in self._fields.keys():
            return self._fields[name].value  # Use the property of the Guy in our managed collection
        else:
            return super().__getattribute__(name)

    def __delattr__(self, name):
        default_list, default_type = self.default_fields()
        if name not in default_list.keys():
            del self._fields[name]
        else:
            raise TypeError("Cannot remove a default field!")

    def change_type(self, name):
        if self._fields[name]._type is str:
            self._fields[name] = Number(None)

        elif self._fields[name]._type is int:
            self._fields[name] = String(None)

        else:
            raise TypeError("Invalid field!")

    def default_fields(self):

        if "sidecar" in self.get_class_name().lower():
            default_list = _getdefault('BIDS_fNIRS_subject_folder.json', "_nirs.json")
            default_type = _getdefault('BIDS_fNIRS_subject_folder_datatype.json', "_nirs.json")
        elif isinstance(self, JSON):
            default_list = _getdefault('BIDS_fNIRS_subject_folder.json', "_" + self.get_class_name().lower() + ".json")
            default_type = _getdefault('BIDS_fNIRS_subject_folder_datatype.json',
                                       "_" + self.get_class_name().lower() + ".json")
        elif isinstance(self, TSV):
            default_list = _getdefault('BIDS_fNIRS_subject_folder.json', "_" + self.get_class_name().lower() + ".tsv")
            default_type = _getdefault('BIDS_fNIRS_subject_folder_datatype.json',
                                       "_" + self.get_class_name().lower() + ".tsv")
        return default_list, default_type

    def get_class_name(self):
        return self.__class__.__name__


class JSON(Metadata):
    """ JSON Class

    Class object that encapsulates subclasses that create and contain BIDS JSON files

    """
    def __init__(self):
        super().__init__()

    def load_from_json(self, fpath):
        with open(fpath) as file:
            fields = json.load(file)
        new = {}
        for name in fields:
            # assume they are all string now
            if String.validate(fields[name]):
                new[name] = String(fields[name])
            elif Number.validate(fields[name]):
                new[name] = Number(fields[name])
            else:
                raise TypeError("Incorrect Datatype")

        self._fields = new

    def save_to_dir(self, info, fpath):

        classname = self.get_class_name().lower() + '.json'
        filedir = _makefiledir(info, classname, fpath)

        fields = {}
        for name in self._fields.keys():
            fields[name] = self._fields[name].value
        with open(filedir, 'w') as file:
            json.dump(fields, file, indent=4)
        self._fields['path2origin'].value = filedir


class TSV(Metadata):
    """ TSV Class

        Class object that encapsulates subclasses that create and contain BIDS TSV files

    """
    def __init__(self):
        super().__init__()

    def save_to_tsv(self, info, fpath):

        classname = self.get_class_name().lower() + '.tsv'
        filedir = _makefiledir(info, classname, fpath)

        ########     VARIABLE DECLARATION     ###########
        fields = list(self._fields)[1:]  # extract all fields
        values = list(self._fields.values())[1:]  # extract all values
        values = [values[i].value for i in range(len(values))]  # organize all values

        ########     VARIABLE ORGANIZATION     ###########
        fieldnames = []  # filter out the fieldnames with empty fields, and organize into row structure
        for i in range(len(fields)):
            if values[i] is not None:
                fieldnames = np.append(fieldnames, fields[i])
        valfiltered = list(filter(None.__ne__, values))  # remove all None fields
        valfiltered = np.transpose(valfiltered)  # tranpose into correct row structure

        ########     TSV FILE WRITING     ###########
        with open(filedir, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, dialect='excel-tab')  # writer setup in tsv format
            writer.writerow(fieldnames)  # write fieldnames
            writer.writerows(valfiltered)  # write rows

    def load_from_tsv(self, fpath):
        rows = []
        with open(fpath, encoding="utf8", errors='ignore') as file:
            csvreader = csv.reader(file)
            names = next(csvreader)

            temp = ''.join(name for name in names)
            if '\ufeff' in temp:
                temp = temp.split('\ufeff')[1]
            rows = temp.split('\t')

            for onerow in csvreader:
                row = ''.join(row for row in onerow)
                row = row.split('\t')
                rows = np.vstack((rows, row))

        for i in range(len(rows[0])):
            onename = rows[0][i]
            self._fields[onename].value = rows[1:, i]


class Coordsystem(JSON):

    def __init__(self, fpath=None):
        if fpath is not None:
            Metadata.__init__(self)
            self.load_from_SNIRF(fpath)
        else:
            Metadata.__init__(self)

    def load_from_SNIRF(self, fpath):
        self._source_snirf = Snirf(fpath)
        self._fields['NIRSCoordinateUnits'].value = self._source_snirf.nirs[0].metaDataTags.LengthUnit


class Optodes(TSV):

    def __init__(self, fpath=None):
        if fpath is not None:
            super().__init__()
            self.load_from_SNIRF(fpath)
        else:
            super().__init__()

    def load_from_SNIRF(self, fpath):
        self._source_snirf = Snirf(fpath)

        self._fields['name'].value = np.append(self._source_snirf.nirs[0].probe.sourceLabels,
                                               self._source_snirf.nirs[0].probe.detectorLabels)
        self._fields['type'].value = np.append(['source'] * len(self._source_snirf.nirs[0].probe.sourceLabels),
                                               ['detector'] * len(self._source_snirf.nirs[0].probe.detectorLabels))
        if self._source_snirf.nirs[0].probe.detectorPos2D is None and \
                self._source_snirf.nirs[0].probe.sourcePos2D is None:
            self._fields['x'].value = np.append(self._source_snirf.nirs[0].probe.sourcePos3D[:, 0],
                                                self._source_snirf.nirs[0].probe.detectorPos3D[:, 0])
            self._fields['y'].value = np.append(self._source_snirf.nirs[0].probe.sourcePos3D[:, 1],
                                                self._source_snirf.nirs[0].probe.detectorPos3D[:, 1])
            self._fields['z'].value = np.append(self._source_snirf.nirs[0].probe.sourcePos3D[:, 2],
                                                self._source_snirf.nirs[0].probe.detectorPos3D[:, 2])
        elif self._source_snirf.nirs[0].probe.detectorPos3D is None and \
                self._source_snirf.nirs[0].probe.sourcePos3D is None:
            self._fields['x'].value = np.append(self._source_snirf.nirs[0].probe.sourcePos2D[:, 0],
                                                self._source_snirf.nirs[0].probe.detectorPos2D[:, 0])
            self._fields['y'].value = np.append(self._source_snirf.nirs[0].probe.sourcePos2D[:, 1],
                                                self._source_snirf.nirs[0].probe.detectorPos2D[:, 1])


class Channels(TSV):
    def __init__(self, fpath=None):
        if fpath is not None:
            super().__init__()
            self.load_from_SNIRF(fpath)
        else:
            super().__init__()

    def load_from_SNIRF(self, fpath):
        self._source_snirf = Snirf(fpath)

        source = self._source_snirf.nirs[0].probe.sourceLabels
        detector = self._source_snirf.nirs[0].probe.detectorLabels
        wavelength = self._source_snirf.nirs[0].probe.wavelengths

        name = []
        label = np.zeros(len(self._source_snirf.nirs[0].data[0].measurementList))
        wavelength_nominal = np.zeros(len(self._source_snirf.nirs[0].data[0].measurementList))

        for i in range(len(self._source_snirf.nirs[0].data[0].measurementList)):
            source_index = self._source_snirf.nirs[0].data[0].measurementList[i].sourceIndex
            detector_index = self._source_snirf.nirs[0].data[0].measurementList[i].detectorIndex
            wavelength_index = self._source_snirf.nirs[0].data[0].measurementList[i].wavelengthIndex

            name.append(source[source_index - 1] + '-' + detector[detector_index - 1] + '-' +
                        str(wavelength[wavelength_index - 1]))
            label[i] = self._source_snirf.nirs[0].data[0].measurementList[i].dataTypeLabel
            wavelength_nominal[i] = wavelength[wavelength_index - 1]

        self._fields['name'].value = name
        self._fields['type'].value = label
        self._fields['source'].value = source
        self._fields['detector'].value = detector
        self._fields['wavelength_nominal'].value = wavelength_nominal
        self._fields['sampling_frequency'].value = np.mean(np.diff(np.array(self._source_snirf.nirs[0].data[0].time)))


    class Events(TSV):
    def __init__(self, fpath=None):
        if fpath is not None:
            super().__init__()
            self.load_from_SNIRF(fpath)
        else:
            super().__init__()

    def load_from_SNIRF(self, fpath):
        self._source_snirf = Snirf(fpath)

        temp = None
        if len(self._source_snirf.nirs[0].stim) > 0:
            for one in self._source_snirf.nirs[0].stim:
                if temp is None:
                    temp = one.data
                else:
                    temp = np.append(temp, one.data, 0)

            temp = temp[np.argsort(temp[:, 0])]
            self._fields['onset'].value = temp[:, 0]
            self._fields['duration'].value = temp[:, 1]
            self._fields['value'].value = temp[:, 2]


class Sidecar(JSON):
    def __init__(self, fpath=None):
        if fpath is not None:
            super().__init__()
            self.load_from_SNIRF(fpath)
        else:
            super().__init__()

    def load_from_SNIRF(self, fpath):
        self._source_snirf = Snirf(fpath)
        self._fields['SamplingFrequency'].value = np.mean(np.diff(np.array(self._source_snirf.nirs[0].data[0].time)))
        self._fields['NIRSChannelCount'].value = len(self._source_snirf.nirs[0].data[0].measurementList)

        if self._source_snirf.nirs[0].probe.detectorPos2D is None \
                and self._source_snirf.nirs[0].probe.sourcePos2D is None:
            self._fields['NIRSSourceOptodeCount'].value = len(self._source_snirf.nirs[0].probe.sourcePos3D)
            self._fields['NIRSDetectorOptodeCount'].value = len(self._source_snirf.nirs[0].probe.detectorPos3D)
        elif self._source_snirf.nirs[0].probe.detectorPos3D is None \
                and self._source_snirf.nirs[0].probe.sourcePos3D is None:
            self._fields['NIRSSourceOptodeCount'].value = len(self._source_snirf.nirs[0].probe.sourcePos2D)
            self._fields['NIRSDetectorOptodeCount'].value = len(self._source_snirf.nirs[0].probe.detectorPos2D)


class Subject(object):

    def __init__(self, fpath=None):
        self.coordsystem = Coordsystem(fpath=fpath)
        self.optodes = Optodes(fpath=fpath)
        self.channel = Channels(fpath=fpath)
        self.sidecar = Sidecar(fpath=fpath)
        self.event = Events(fpath=fpath)

        self.subinfo = {
            'sub-': _pull_label(fpath, 'sub-'),
            'ses-': _pull_label(fpath, 'ses-'),
            'task-': self.pull_task(fpath),
            'run-': _pull_label(fpath, 'run-')
        }

    def pull_task(self, fpath=None):
        if self.sidecar.TaskName is None:
            return _pull_label(fpath, 'task-')
        else:
            return self.sidecar.TaskName

    def load_sub_folder(self, fpath):
        # no point in making this function currently.
        # We would have to access directory which is not ideal for cloud purposes

        # subj = dict({'nirs': {'Coordsystem': self.coordsystem.load_from_json(fpath+'/nirs/sub-'+self.subinfo.get('sub-')+'_coordsystem.json'),
        #                       'Optodes': self.optodes.load_from_tsv(fpath+'/nirs/sub-'+self.subinfo.get('sub-')+'_optodes.tsv'),
        #                       'Channels': self.channel.load_from_tsv(fpath+'/nirs/sub-'+self.subinfo.get('sub-')+'_channels.tsv')},
        #                         'scans': None})

        pass

    def load_from_snirf(self, fpath):
        # self.subinfo = _check_empty_field(self.subinfo)
        self.coordsystem.load_from_SNIRF(fpath)
        self.optodes.load_from_SNIRF(fpath)
        self.channel.load_from_SNIRF(fpath)
        self.sidecar.load_from_SNIRF(fpath)

    def validate(self):
        # Sreekanth supposedly has it
        pass