from tkinter import Frame, Scrollbar, Text, PhotoImage, Label
from fitz import Document
from threading import Thread


class ShowPdf:
    img_object_li = []
    current_page = 0
    no_of_pages = 0
    dpi = 100

    def __init__(self):
        self.text = None
        self.frame = None
        self.title_bar = None
        self.current_page_title = None

    def pdf_view(self, master, pdf_location):
        self.frame = Frame(master)

        scroll_y = Scrollbar(self.frame, orient="vertical")
        scroll_x = Scrollbar(self.frame, orient="horizontal")

        scroll_x.pack(fill="x", side="bottom")
        scroll_y.pack(fill="y", side="right")

        self.title_bar = Frame(self.frame, height=20, background='white')
        self.title_bar.pack(side='top', fill='x')

        def switch_page(n):
            if (self.current_page == 0 and n == -1) or (self.current_page+1 == self.no_of_pages and n == 1):
                return

            destroy_text()
            create_text()
            master.after(250, start_pack(self.current_page + n))

        previous_page = Label(self.title_bar, text='Previous Page', background='#202020', foreground='white')
        previous_page.pack(anchor='w', padx=(0, 10), side='left')
        previous_page.bind('<Button-1>', lambda e: switch_page(-1))

        next_page = Label(self.title_bar, text='Next Page', background='#202020', foreground='white')
        next_page.pack(anchor='nw', side='left')
        next_page.bind('<Button-1>', lambda e: switch_page(1))

        self.current_page_title = Label(self.title_bar, text='')
        self.current_page_title.pack()

        def create_text():
            self.text = Text(self.frame, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
            self.text.pack(fill='both', expand=True, anchor='center')

            scroll_x.config(command=self.text.xview)
            scroll_y.config(command=self.text.yview)

        def destroy_text():
            self.text.destroy()

        create_text()

        def add_img(n):
            self.img_object_li.clear()

            open_pdf = Document(pdf_location)

            self.no_of_pages = open_pdf.page_count

            timg = open_pdf.load_page(n)
            timg = timg.get_pixmap(dpi=self.dpi)
            timg = timg.pil_tobytes('ppm')
            timg = PhotoImage(data=timg)
            self.img_object_li.append(timg)

            for i in self.img_object_li:
                self.text.image_create('end', image=i)
                self.text.insert('end', "\n\n")
            self.current_page_title.config(text=f'Page {self.current_page+1}/{self.no_of_pages}')
            self.text.configure(state="disabled")

        def start_pack(n):
            self.current_page = n
            t1 = Thread(target=add_img, args=[n])
            t1.start()

        master.after(250, start_pack(0))

        return self.frame

    def set_dpi(self, n):
        if n is None:
            return
        if n > 500:
            raise ValueError('Program is set to not load dpi higher than 500')

        self.dpi = n


if __name__ == '__main__':
    from tkinter import Tk

    window = Tk()
    window.geometry('900x600')
    d = ShowPdf()
    d.set_dpi(None)
    pdf = d.pdf_view(window, pdf_location=r"C:\Users\USER\Downloads\marksheet_3rdsem.pdf")
    pdf.pack(fill='both', expand=True)
    window.mainloop()
