/* eslint-disable */
import styled from 'styled-components';
import styles from "./citation.module.scss";
import { PDFDocumentProxy } from 'pdfjs-dist';
import { TextItem } from 'pdfjs-dist/types/src/display/api';
import { pdfjs } from 'react-pdf';
import { useNavigate } from 'react-router-dom';

// pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const CitationLink = styled.a`
  color: #007bff;
  text-decoration: underline;
  margin-right: 10px;
  &:hover {
    color: #0056b3;
    text-decoration: underline;
  }
`;

interface Props {
  url: string;
  text: string;
}
export interface MetaData {
    meta: string[];
}
interface MatchResult {
pageNumber: number;
score: number;
}

function createWordMatchRegex(searchString: string): RegExp {
    // Split the searchString into words
    const words = searchString.split(/\s+/).filter(word => word.length > 4);
    //console.log(words);
    
    // Escape special regex characters in each word
    const escapedWords = words.map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    
    
    const pattern = escapedWords.join('|');
    
    // Create and return the regex
    return new RegExp(`\\b(${pattern})\\b`, 'i');
  }
export const getMatchScore = (text: string, regex: string, index: number): number => {
    const words = regex.split(" ");
    const validWords = words.map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    let ans = 0;
    for(var i of validWords){
        if(text && text.match(i) && i &&  i.length>1){
            const match = text.match(i);
            const a = match ? match.length : 0;
            ans += a;
        }
    }
    //console.log(matches);
    return ans;
  };
export const findBestMatchingPage = async (pdfDocument: any, searchString: string): Promise<number> => {
    //console.log(searchString);
    //console.log(searchString.replace(/\n/g, " "));
    let bestMatch: MatchResult = { pageNumber: 1, score: 0 };
  
    for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber++) {
      const page = await pdfDocument.getPage(pageNumber);
      const textContent = await page.getTextContent();
      const textItems = textContent.items.filter((item: any): item is TextItem => 'str' in item).map((item: { str: any; }) => item.str).join(' ');
      const regex = searchString.replace(/\n/g, " ");
      const score = getMatchScore(textItems, regex, pageNumber);
  
      if (score > bestMatch.score) {
        bestMatch = { pageNumber, score };
      }
    }
    //console.log(t.match(s));
    console.log(bestMatch);
    return bestMatch.pageNumber;
};
export const openPDFAtBestMatch = async (pdfUrl: string, pageNumber: string) => {
  try {
    

    //const urlWithPage = `${pdfUrl}#page=${bestPage}`;
    window.open(`/file?url=${encodeURIComponent(pdfUrl)}&pagenum=${encodeURIComponent(pageNumber)}`, '_blank');
  } catch (error) {
      console.error("Error loading PDF:", error);
      // Handle the error appropriately, e.g., show a user-friendly message
  }

  };
export const getPDFLinks = (citations: string ) : ({pdfURL: string, pageNum: string}[]) => {
  if(citations=="" || citations == "{}"){
    return [];
  }else{
    citations = citations.replace(/\n/g, " ");
    const jsonString = JSON.parse(JSON.parse(JSON.stringify(citations)));
    return Object.keys(jsonString).map((key, index) => {
      return {
        pdfURL : "https://rag-prod-ingested-docs.s3.ap-south-1.amazonaws.com/"+jsonString[key]["doc_name"]+".pdf",
        pageNum : jsonString[key]["page_num"],
      }
    })
  }
}
export const Citations = ({response}:{response: string}): any => {
    //console.log(response);
    const handleFileClick = (url: string) => {
        window.open(url, '_blank');
      };
    if(response==""){
      return <div></div>;
    }
    const citations = response.replace(/\n/g, " ");
    const jsonString = JSON.parse(JSON.parse(JSON.stringify(citations)));
    //console.log(jsonString);
    // console.log(typeof(jsonString));
    // console.log(Object.keys(jsonString));
    const history = useNavigate();
    if(Object.keys.length==0){
      return <div></div>;
    }
    return (<div className='grid grid-cols-2 gap-2 w-[80%]'>
        {Object.keys(jsonString).map((key,index)=>{
            console.log(key);
            console.log(jsonString[key]);
            const fileName = jsonString[key]["doc_name"].endsWith('.md') 
                ? jsonString[key]["doc_name"].slice(0, -3) 
                : jsonString[key]["doc_name"];
            return (<div className={`flex flex-col p-1 rounded-lg bg-slate-100 border border-solid border-slate-300 shadow-md hover:shadow-lg transition-shadow duration-300 ${styles.row}`} 
                         key={key+index}
                         onClick={() => window.open(`https://rag-prod-ingested-docs.s3.ap-south-1.amazonaws.com/${fileName}.pdf#page=${jsonString[key]["page_num"]}`, '_blank')}
                    >
                      <div className={`text-white text-sm bg-slate-100 font-small ${styles.citation}`}>
                          <div className="truncate">
                            {index + 1}: {fileName}.pdf
                          </div>
                          <div>
                            Page Number : {jsonString[key]["page_num"]}
                          </div>
                      </div>
                      {/* <div className={`text-sm ${styles.citation}`}>
                        {jsonString[key]["chunk"]}
                      </div> */}
                    {/* {
                      <div>
                          <div className={styles.sourceFile}><div>{(index+1)}: {" "} </div>{ " " + jsonString[key]["file_name"]}.pdf</div>
                          <div className={styles.citation}>
                              {jsonString[key]["chunk"]}
                          </div>
                      </div>
                    } */}
            </div>);
        })}
    </div>);


}
const Citation = ({ url, text, response }:{url:string, text:string, response: string}) => {

    //deserialize(a);
    return (
    <div>
      
      <Citations response={response}></Citations>
    </div>
  );
};

export default Citation;

