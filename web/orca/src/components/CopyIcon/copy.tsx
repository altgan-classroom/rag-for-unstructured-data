import { useCallback, useState } from "react";
import { Button } from "../Button";
import { Img } from "../Img";
import styles from "./copy.module.css";

interface CopyIconProps {
    textToCopy: string;
}
  
const useCopyToTick = () => {
    const [isCopied, setIsCopied] = useState(false);
  
    const handleCopy = useCallback((text: string) => {
      navigator.clipboard.writeText(text)
        .then(() => {
          setIsCopied(true);
          setTimeout(() => setIsCopied(false), 3000);
        })
        .catch(err => console.error('Failed to copy: ', err));
    }, []);
  
    return { isCopied, handleCopy };
};
const CopyIcon = ({ textToCopy }: CopyIconProps) => {
    const { isCopied, handleCopy } = useCopyToTick();

    return (<div className="flex flex-row">
        {!isCopied ? <Button
        rightIcon={
            <Img src="/images/img_phcopyduotone.svg" alt="Ph:copy-duotone" className="h-[16px] w-[16px]" />
        }
        className={styles.button}
        onClick={()=>handleCopy(textToCopy)}
        >
        </Button> : <div className="flex flex-row text-sm">
            <Img src="/images/copied_icon.svg" alt="Ph:copy-duotone" className="h-[16px] w-[16px]" />
        </div>}
    </div>);



}
export default CopyIcon;