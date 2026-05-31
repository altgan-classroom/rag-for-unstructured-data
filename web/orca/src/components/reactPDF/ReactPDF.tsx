/* eslint-disable */
import { useEffect, useRef, useState } from 'react';
import {Document, Page,pdfjs } from 'react-pdf';
//import { Document } from 'react-pdf/dist/esm';
import "./reactPDF.css";
import loadingSpinner from "../../assets/loadingSpinner.gif";
import samplePDF from '../../assets/files/meta.pdf';
//import { PDFDocument } from 'pdf-lib';
import { PDFDocumentProxy } from 'pdfjs-dist';
import { TextContent, TextItem, TextMarkedContent } from 'pdfjs-dist/types/src/display/api';
import { useLocation } from 'react-router-dom';
import LoadingSpinner from '../LoadingSpinner/loadingSpinner';
import { findBestMatchingPage } from '../Citation';


pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString();

const CustomPage = ({ pageNumber, pdfDocument }:{pageNumber:number, pdfDocument:PDFDocumentProxy}) => {
    const [textItems, setTextItems] = useState<(TextItem | TextMarkedContent)[]>([]);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
  
    useEffect(() => {
      const loadPageText = async () => {
        if (pdfDocument && canvasRef.current) {
          const page = await pdfDocument.getPage(pageNumber);
          const viewport = page.getViewport({ scale: 1 });
          const canvas = canvasRef.current;
          const context = canvas.getContext('2d');
  
          if (context) {
            canvas.height = viewport.height;
            canvas.width = viewport.width;
  
            const renderContext = {
              canvasContext: context,
              viewport: viewport,
            };
  
            await page.render(renderContext).promise;
  
            const textContent:TextContent | TextMarkedContent = await page.getTextContent();
            setTextItems(textContent.items);
          }
        }
      };
  
      loadPageText();
    }, [pdfDocument, pageNumber]);
  
    // useEffect(() => {
    //   const canvas = canvasRef.current;
    //   if (canvas) {
    //     const context : CanvasRenderingContext2D | null = canvas.getContext('2d');
        
    //     if (context) {
    //       const renderHighlights = () => {
    //         context.clearRect(0, 0, canvas.width, canvas.height);
    //         //console.log(canvas.height);
    //         //console.log(canvas.width);
    //         let isHighlighted = false;
            
    //           //console.log(item);
    //           //console.log(searchText.split(" ")[0]);
    //         const searchWord = searchText.split(" ")[0].toLowerCase();
    //         const isTextItem = (item: TextItem | TextMarkedContent): item is TextItem => 'str' in item;
    //         //searchText.split(" ").forEach((searchWord) =>{
    //         // console.log(textItems[0]);
    //         textItems.forEach((item) => {

    //           if (isTextItem(item) && item.str){
    //             let isIncluded: boolean = true;
    //             let c = 0;
    //             for(var i=0;i<item.str.split(" ").length;i++){
    //               if(searchText.includes(item.str.split(" ")[i])){
    //                 c = c +1;
    //               }
    //               else{
    //                 isIncluded = false;
    //               }
    //             }
    //             if(isIncluded){
    //               const { transform, width, height } = item;
    //               const currentX = transform[4];
    //               const y = transform[5];
    //               context.fillStyle = 'yellow';
    //               context.globalAlpha = 0.5;
    //               context.fillRect(currentX, canvas.height-y-12, width, height);
    //             }
    //           }
    //           //console.log(item);
    //           if (isTextItem(item) && item.str && item.str.includes("roadmap")) {
    //             const words = item.str.split(' ');
    //             //console.log(item);
    //             //console.log(searchWord);
    //             const { transform, width, height } = item;
    //             //console.log(transform);
    //             let currentX = transform[4];
    //             const y = transform[5];
    //             words.forEach((word) => {
    //               //console.log(word);
    //               const width = context.measureText(word).width;
    //               // console.log(word);
    //               // console.log(width);
    //               // console.log(currentX);
    //               if (word.toLowerCase().includes("we")) {
    //                 // console.log(word);
    //                 // console.log(width);
    //                 const newWidth = context.measureText("have").width;
    //                 context.fillStyle = 'yellow';
    //                 context.globalAlpha = 0.5;
    //                 context.fillRect(currentX, canvas.height - y - 16, newWidth, height);
    //               }
    //               currentX += width;
    //             });
    //             //console.log(x + "hi" + y);
                
    //           }
    //         });
    //         let curIndex = 0;
    //           // for(let i=0;i<textItems.length; i++){
    //           //     if(isTextItem(textItems[i])){
    //           //       if(textItems[i].str && textItems[i].str.includes(searchWord)){
    //           //           console.log(textItems[i]);
    //           //       }
    //           //     }
                  
    //           // }
              
    //         //});
    //         for(var word of searchText.split(" ")){
    //           for(let i=0;i<textItems.length; i++){
    //             if(isTextItem(textItems[i])){
    //               // if(textItems[i].str && textItems[i].str.includes(searchWord)){
    //               //     //console.log(textItems[i]);
    //               // }
    //             }
    //           }
    //         }
    //           // if(isTextItem(item) && item.str && item.str.toLowerCase().includes("competition")) {
    //           //     // console.log(item);
    //           //     // console.log(searchText);
    //           //     const { transform, width, height } = item;
    //           //     //console.log(transform);
    //           //     const x = transform[4];
    //           //     const y = transform[5];
    //           //     //console.log(x + "hi" + y);
    //           //     if(!isHighlighted){
    //           //         console.log(item);
    //           //         console.log(canvas.height);
    //           //         context.fillStyle = 'yellow';
    //           //         context.globalAlpha = 0.5;
    //           //         context.fillRect(x-10>100? 10: x, canvas.height-y-16, width, height);
    //           //     }
    //           //     isHighlighted = true;
    //           // }
              
            
    //       };
  
    //       renderHighlights();
    //     }
    //   }
    // }, [textItems, searchText]);
  
    return (
      <div style={{ position: 'relative' }}>
        <canvas ref={canvasRef} style={{ position: 'absolute', zIndex: 1 }} />
        <Page pageNumber={pageNumber} width={600} renderAnnotationLayer={false} renderTextLayer={false}/>
      </div>
    );
  };
  
// function highlightPattern(text:string, pattern:string) {
//     return text.replace(pattern, (value) => `<mark>${value}</mark>`);
// }

export default function PdfViewer() {
    const useQuery = (): URLSearchParams => {
        return new URLSearchParams(useLocation().search);
        };
    const query = useQuery();
    const url = query.get('url') || '';
    const pageNumberUrl = query.get('pagenum') || '';
    //const regex = searchText.replace(/\n/g, " ");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    // console.log("Hello      " + searchText);
    // console.log(import.meta.url);
    // console.log("hi");
    //const [pdfBytes, setPdfBytes] = useState<Uint8Array | null>(null);
    const [numPages, setNumPages] = useState<number>(0);
    const [pageNumber, setPageNumber] = useState<number>(0);
    //const pageNumber = useState<number>(pageNumberInUrl);
    //const [file,setFile] = useState<Uint8Array>();

    const [pdfDocument, setPdfDocument] = useState<any>();

    useEffect(() => {
      const fetchPDFFromURL = async () => {
        setIsLoading(true);
        try {
          const loadingTask = pdfjs.getDocument(url);
          const pdfDocument = await loadingTask.promise;
          //const bestPageNumber = await findBestMatchingPage(pdfDocument, searchText);
          setPageNumber(Number(pageNumberUrl));
          //const loadingTask = pdfjs.getDocument(url);
          setPdfDocument(pdfDocument);
        } catch (error) {
          console.error('Error loading PDF:', error);
        } finally {
          setIsLoading(false);
        }
      };

      fetchPDFFromURL();
    }, [url]);

    function onDocumentLoadSuccess({ numPages }: {numPages: number}) {
      setNumPages(numPages);
      //setPageNumber(1);
    }
    if (isLoading) {
      return (
      <div>
        <LoadingSpinner />
      </div>);
    }

  return (
    <>
      {pdfDocument && <div className='documentContainer'><Document
        file={url}
        onLoadSuccess={onDocumentLoadSuccess}
        renderMode='canvas'
      >
        <CustomPage pageNumber={pageNumber} pdfDocument={pdfDocument} />
        {/* <Page pageNumber={pageNumber} renderTextLayer={true} renderAnnotationLayer={false} customTextRenderer={textRenderer}/> */}
      </Document>
      <div>
        <p>
          Page {pageNumber || (numPages ? 1 : '--')} of {numPages || '--'}
        </p>
        {/* <button
          type="button"
          onClick={previousPage}
        >
          Previous
        </button>
        <button
          type="button"
          disabled={pageNumber >= numPages}
          onClick={nextPage}
        >
          Next
        </button> */}
      </div>
      {/* <PdfLoader url={url} beforeLoad={<div><img src={loadingSpinner} alt="Loading..." className="loading-spinner" /></div>}>
      {(pdfDocument) => (
        <PdfHighlighter
          pdfDocument={pdfDocument}
          enableAreaSelection={(event) => event.altKey}

          //scrollRef={highlighterUtilsRef}
          highlights={highlights}
        />
      )}
    </PdfLoader> */}
      </div>}
      
    </>
  );
}

// const fetchAndHighlightPDF = async (url: string, text: string) => {
//     const existingPdfBytes = await fetch(url).then((res) => res.arrayBuffer());
//     const pdfDoc = await PDFDocument.load(existingPdfBytes);
//     const pages = pdfDoc.getPages();
  
//     for (const page of pages) {
//       const { textContent, textContentItemsStr } = await page.getTextContent();
//       for (let i = 0; i < textContentItemsStr.length; i++) {
//         if (textContentItemsStr[i] === text) {
//           const item = textContent.items[i];
//           const { width, height, transform } = item;
//           const [x, y] = transform;
  
//           page.drawRectangle({
//             x,
//             y: y - height,
//             width,
//             height,
//             color: rgb(1, 1, 0),
//             opacity: 0.5,
//           });
//         }
//       }
//     }
  
//     return await pdfDoc.save();
//   };