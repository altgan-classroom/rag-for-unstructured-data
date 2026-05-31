import { Text } from "./..";
import React from "react";

interface Props {
  className?: string;
  marketingText?: React.ReactNode;
}

export default function MarketingText({ marketingText = "Marketing", ...props }: Props) {
  return (
    <div {...props} className={`${props.className} flex items-start w-[32%] md:w-full p-2.5 bg-gray-900_04 rounded`}>
      <Text as="p" className="mb-9 tracking-[0.15px] !text-white-a700_7f">
        {marketingText}
      </Text>
    </div>
  );
}
