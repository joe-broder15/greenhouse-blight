class Job:
    def __init__(self, title: str, company: str, second_line: str, link: str, software: str):
        self.company = company
        self.software = software
        self.title = title
        self.second_line = second_line
        self.link = link

    def __str__(self):
        return f"{self.company},{self.software},{self.title},{self.second_line},{self.link}"

    def __repr__(self):
        return self.__str__()


