#include "dram_cntlr.h"
#include "memory_manager.h"
#include "core.h"
#include "log.h"
#include "subsecond_time.h"
#include "stats.h"
#include "fault_injection.h"
#include "shmem_perf.h"

#if 0
   extern Lock iolock;
#  include "core_manager.h"
#  include "simulator.h"
#  define MYLOG(...) { ScopedLock l(iolock); fflush(stdout); printf("[%s] %d%cdr %-25s@%3u: ", itostr(getShmemPerfModel()->getElapsedTime()).c_str(), getMemoryManager()->getCore()->getId(), Sim()->getCoreManager()->amiUserThread() ? '^' : '_', __FUNCTION__, __LINE__); printf(__VA_ARGS__); printf("\n"); fflush(stdout); }
#else
#  define MYLOG(...) {}
#endif

class TimeDistribution;

namespace PrL1PrL2DramDirectoryMSI
{

DramCntlr::DramCntlr(MemoryManagerBase* memory_manager,
      ShmemPerfModel* shmem_perf_model,
      UInt32 cache_block_size,AddressHomeLookup* _address_home_lookup)
   : DramCntlrInterface(memory_manager, shmem_perf_model, cache_block_size)
   , m_reads(0)
   , m_writes(0)
   , address_home_lookup(_address_home_lookup)

{
   m_dram_perf_model = DramPerfModel::createDramPerfModel(
         memory_manager->getCore()->getId(),
         cache_block_size, address_home_lookup);

   m_fault_injector = Sim()->getFaultinjectionManager()
      ? Sim()->getFaultinjectionManager()->getFaultInjector(memory_manager->getCore()->getId(), MemComponent::DRAM)
      : NULL;

   m_dram_access_count = new AccessCountMap[DramCntlrInterface::NUM_ACCESS_TYPES];
   registerStatsMetric("dram", memory_manager->getCore()->getId(), "reads", &m_reads);
   registerStatsMetric("dram", memory_manager->getCore()->getId(), "writes", &m_writes);
}

DramCntlr::~DramCntlr()
{
   printDramAccessCount();
   delete [] m_dram_access_count;

   delete m_dram_perf_model;
}

boost::tuple<SubsecondTime, HitWhere::where_t>
DramCntlr::getDataFromDram(IntPtr address, core_id_t requester, Byte* data_buf,
                           SubsecondTime now, ShmemPerf *perf,
                           bool is_metadata, int blocktype)
{
    // When a demand arrives, it hits if DRAM has already completed the earlier fetch
    auto it = m_dram_addresses.find(address);
    if (it != m_dram_addresses.end() && blocktype == CacheBlockInfo::PAGE_TABLE)
    {
        SubsecondTime ready_time = it->second.first;
        SubsecondTime issued_at = it->second.second;

        std::cout << "Address 0x" << std::hex << address << std::dec
                  << "type, " << ((blocktype != CacheBlockInfo::NON_PAGE_TABLE) ? "NON_PT" : "OTHER")
                  << " demand " << now.getNS() << " ns, ready at "
                  << ready_time.getNS() << " ns, issued at " << issued_at.getNS() << " ns\n";

         ++m_reads;
         m_dram_addresses.erase(it);
         
         SubsecondTime latency = (ready_time > now) ? (ready_time - now) : SubsecondTime::Zero();

         return {latency, HitWhere::DRAM};
        // If you ever want to model “arrived too early”, you can return (ready_time - now)
        // or let normal DRAM path handle it.
    }

    SubsecondTime dram_access_latency = runDramPerfModel(requester, now, address, READ, perf, is_metadata);

    ++m_reads;

    if(blocktype == CacheBlockInfo::PREFETCH_PAGE_TABLE)
    {
      std::cout << "Track type, " << ((blocktype == CacheBlockInfo::PREFETCH_PAGE_TABLE) ? "PREFETCH_PAGE_TABLE" : "OTHER") << ", address, " <<std::hex<< address <<std::dec<< '\n';
      // Store completion time in DRAM's timeline: ready_time, issue_time
      m_dram_addresses[address] = {now + dram_access_latency, now};
    }
    

    return {dram_access_latency, HitWhere::DRAM};
}


boost::tuple<SubsecondTime, HitWhere::where_t>
DramCntlr::putDataToDram(IntPtr address, core_id_t requester, Byte* data_buf, SubsecondTime now,bool is_metadata, int blocktype)
{
   if (Sim()->getFaultinjectionManager())
   {
      if (m_data_map[address] == NULL)
      {
         LOG_PRINT_ERROR("Data Buffer does not exist");
      }
      memcpy((void*) m_data_map[address], (void*) data_buf, getCacheBlockSize());

      // NOTE: assumes error occurs in memory. If we want to model bus errors, insert the error into data_buf instead
      if (m_fault_injector)
         m_fault_injector->postWrite(address, address, getCacheBlockSize(), (Byte*)m_data_map[address], now);
   }
   SubsecondTime dram_access_latency = runDramPerfModel(requester, now, address, WRITE, &m_dummy_shmem_perf,is_metadata);

   ++m_writes;
   #ifdef ENABLE_DRAM_ACCESS_COUNT
   addToDramAccessCount(address, WRITE);
   #endif
   MYLOG("W @ %08lx", address);

   return boost::tuple<SubsecondTime, HitWhere::where_t>(dram_access_latency, HitWhere::DRAM);
}

SubsecondTime
DramCntlr::runDramPerfModel(core_id_t requester, SubsecondTime time, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf, bool is_metadata)
{
   UInt64 pkt_size = getCacheBlockSize();
   
   SubsecondTime dram_access_latency = m_dram_perf_model->getAccessLatency(time, pkt_size, requester, address, access_type, perf,is_metadata);
   return dram_access_latency;
}

void
DramCntlr::addToDramAccessCount(IntPtr address, DramCntlrInterface::access_t access_type)
{
   m_dram_access_count[access_type][address] = m_dram_access_count[access_type][address] + 1;
}

void
DramCntlr::printDramAccessCount()
{
   for (UInt32 k = 0; k < DramCntlrInterface::NUM_ACCESS_TYPES; k++)
   {
      for (AccessCountMap::iterator i = m_dram_access_count[k].begin(); i != m_dram_access_count[k].end(); i++)
      {
         if ((*i).second > 100)
         {
            LOG_PRINT("Dram Cntlr(%i), Address(0x%x), Access Count(%llu), Access Type(%s)",
                  m_memory_manager->getCore()->getId(), (*i).first, (*i).second,
                  (k == READ)? "READ" : "WRITE");
         }
      }
   }
}

}
