from rasa.shared.core.slots import Slot

class PhoneNumber(Slot):
    def feature_dimensionality(self):
        return 2

    def as_feature(self):
        r = [0.0] * self.feature_dimensionality()
        if self.value:
            if len(self.value) >= 10 & len(self.value) <= 12:
                r[0] = 1.0
        return r

class AgeNumber(Slot):
    def feature_dimensionality(self):
        return 2

    def as_feature(self):
        r = [0.0] * self.feature_dimensionality()
        if self.value:
            if len(self.value) >= 1 & len(self.value) <= 4:
                r[0] = 1.0
            else:
                r[1] = 1.0
        return r